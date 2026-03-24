"use server";

export async function sendMessage(message: string) {
  try {
    const response = await fetch("http://localhost:8000/api/v1/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error in sendMessage action:", error);
    throw error;
  }
}
