import { BrowserRouter } from "react-router-dom";
import Layout from "./components/Layout";
import AppRoutes from "./routes";

export default function App() {
    return (
        <BrowserRouter>
            <Layout>
                <AppRoutes />
            </Layout>
        </BrowserRouter>
    );
}