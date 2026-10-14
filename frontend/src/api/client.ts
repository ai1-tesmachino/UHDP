import axios from "axios";

const pageHost = window.location.hostname;
const apiHost = !pageHost || pageHost === "localhost" ? "127.0.0.1" : pageHost;

const api = axios.create({
    baseURL: `${window.location.protocol}//${apiHost}:8000`
});

export default api;