import api from "./client";

export async function getDevices() {
    const response = await api.get(
        "/devices/"
    );

    return response.data;
}