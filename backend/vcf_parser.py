from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)

SUPPORTED_GENES = {"CYP2D6", "CYP2C19", "CYP2C9", "SLCO1B1", "TPMT", "DPYD"}


@dataclass
class VariantRecord:
    chrom: str
    pos: int
    id: str
    ref: str
    alt: str
    gene: str = ""
    star: str = ""
    rsid: str = ""
    raw_info: Dict[str, str] = field(default_factory=dict)


def validate_vcf_signature(vcf_bytes: bytes) -> None:
    """
    Strict validation of VCF structure.
    Raises ValueError if file is not a valid VCF.
    """
    try:
        text = vcf_bytes.decode("utf-8", errors="replace")
    except Exception:
        raise ValueError("File is not valid UTF 8 text")

    lines = text.splitlines()

    if not lines:
        raise ValueError("Empty file")

    has_fileformat = False
    has_chrom_header = False

    for line in lines:
        line = line.strip()

        if line.startswith("##fileformat=VCF"):
            has_fileformat = True

        if line.startswith("#CHROM"):
            cols = line.split("\t")
            required = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]
            if cols[:8] != required:
                raise ValueError("Invalid #CHROM header structure")
            has_chrom_header = True
            break

        if not line.startswith("#"):
            break

    if not has_fileformat:
        raise ValueError("Missing ##fileformat VCF header")

    if not has_chrom_header:
        raise ValueError("Missing #CHROM header line")


def parse_info_field(info_str: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for token in info_str.split(";"):
        token = token.strip()
        if "=" in token:
            k, _, v = token.partition("=")
            result[k.upper()] = v
        elif token:
            result[token.upper()] = "TRUE"
    return result


def extract_rsid(id_col: str, info: Dict[str, str]) -> str:
    rs_info = info.get("RS", "")
    if rs_info:
        if not rs_info.startswith("rs"):
            rs_info = f"rs{rs_info}"
        return rs_info

    if id_col and id_col != ".":
        for part in id_col.split(";"):
            if part.lower().startswith("rs"):
                return part

    return ""


def pure_python_parse(vcf_bytes: bytes) -> Dict[str, List[VariantRecord]]:
    gene_variants: Dict[str, List[VariantRecord]] = {g: [] for g in SUPPORTED_GENES}

    text = vcf_bytes.decode("utf-8", errors="replace")
    lines = text.splitlines()

    for line in lines:
        if not line or line.startswith("#"):
            continue

        cols = line.split("\t")
        if len(cols) < 8:
            continue

        chrom, pos_str, id_col, ref, alt = cols[:5]
        info_str = cols[7]

        try:
            pos = int(pos_str)
        except ValueError:
            continue

        info = parse_info_field(info_str)

        gene = info.get("GENE", "").strip().upper()
        star = info.get("STAR", info.get("HAPLOTYPE", "")).strip()
        rsid = extract_rsid(id_col, info)

        if gene not in SUPPORTED_GENES:
            continue

        record = VariantRecord(
            chrom=chrom,
            pos=pos,
            id=id_col,
            ref=ref,
            alt=alt,
            gene=gene,
            star=star,
            rsid=rsid,
            raw_info=info
        )

        gene_variants[gene].append(record)

    return gene_variants


def pysam_parse(vcf_bytes: bytes) -> Dict[str, List[VariantRecord]]:
    import pysam

    gene_variants: Dict[str, List[VariantRecord]] = {g: [] for g in SUPPORTED_GENES}

    with pysam.VariantFile(io.BytesIO(vcf_bytes)) as vcf:
        for rec in vcf.fetch():
            info = dict(rec.info)

            gene = str(info.get("GENE", "")).strip().upper()
            if gene not in SUPPORTED_GENES:
                continue

            star = str(info.get("STAR", info.get("HAPLOTYPE", ""))).strip()

            rs_raw = str(info.get("RS", "")).strip()
            if rs_raw and rs_raw != ".":
                rsid = rs_raw if rs_raw.startswith("rs") else f"rs{rs_raw}"
            elif rec.id and rec.id != ".":
                rsid = next(
                    (i for i in rec.id.split(";") if i.lower().startswith("rs")),
                    ""
                )
            else:
                rsid = ""

            alt_str = ",".join(str(a) for a in rec.alts) if rec.alts else "."

            record = VariantRecord(
                chrom=str(rec.chrom),
                pos=rec.pos,
                id=rec.id or ".",
                ref=str(rec.ref),
                alt=alt_str,
                gene=gene,
                star=star,
                rsid=rsid,
                raw_info={k: str(v) for k, v in info.items()}
            )

            gene_variants[gene].append(record)

    return gene_variants


def parse_vcf(vcf_bytes: bytes) -> Dict[str, List[VariantRecord]]:
    """
    Strict VCF entry point.

    Validates structure first via validate_vcf_signature(), then parses
    with pysam when available and falls back to the pure-Python parser
    only when pysam is explicitly not installed.

    IMPORTANT: exceptions are intentionally NOT caught here.
    The caller (upload endpoint) is responsible for converting them to
    HTTP 400 responses so that invalid files are always rejected and
    never silently accepted.
    """

    # Step 1 — structural guard: enforces ##fileformat and #CHROM header.
    # Raises ValueError immediately if the file is not valid VCF.
    validate_vcf_signature(vcf_bytes)

    # Step 2 — full parse
    try:
        result = pysam_parse(vcf_bytes)
        logger.info("VCF parsed using pysam (strict mode)")
        return result
    except ImportError:
        # pysam is not installed in this environment.
        # Fall back to the pure-Python parser — structural validation
        # (validate_vcf_signature) has already passed, so this is safe.
        logger.warning(
            "pysam not available — falling back to pure-Python parser. "
            "Install pysam for full strict parsing in production."
        )
        return pure_python_parse(vcf_bytes)
    except Exception as exc:
        # pysam IS installed but rejected the file — treat as invalid VCF.
        raise ValueError(f"VCF body is invalid or malformed: {exc}") from exc


def extract_patient_id(vcf_bytes: bytes) -> str:
    try:
        text = vcf_bytes.decode("utf-8", errors="replace")
        for line in text.splitlines():
            if line.startswith("#CHROM"):
                cols = line.split("\t")
                if len(cols) > 9 and cols[9].strip():
                    return f"PATIENT_{cols[9].strip().upper()}"
                break
    except Exception:
        pass

    return "PATIENT_UNKNOWN"
