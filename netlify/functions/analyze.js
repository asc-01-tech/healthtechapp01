
export async function handler(event) {
    if (event.httpMethod !== "POST") {
        return {
            statusCode: 405,
            body: "Method Not Allowed"
        }
    }

    return {
        statusCode: 200,
        body: JSON.stringify({
            status: "Analyze endpoint operational"
        })
    }
}
