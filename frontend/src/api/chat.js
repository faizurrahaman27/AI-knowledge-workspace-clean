import api from "./axios";

export async function askQuestion(question) {

    const response = await api.post(
        `/chat/?question=${encodeURIComponent(question)}`
    );

    return response.data;
}