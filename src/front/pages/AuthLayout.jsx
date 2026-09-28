import { Outlet } from "react-router-dom";

// Frame shared by login, register, forgot and reset pages: brand panel + card.
export const AuthLayout = () => {
    return (
        <div className="io-auth">
            <section className="io-auth-panel">
                <div className="d-flex align-items-center gap-2">
                    <span className="io-brand-mark" style={{ width: 36, height: 36 }}>
                        <i className="fa-solid fa-check text-white"></i>
                    </span>
                    <span className="io-brand-name" style={{ fontSize: 26 }}>InvoiceOps</span>
                </div>

                <div>
                    <h1 className="mb-4">Cierre de mes en 10 minutos.</h1>
                    <p className="fs-5 mb-4">
                        Registra la actividad de cada cliente, aplica su contrato y genera las
                        propuestas de facturación listas para tu programa de facturas.
                    </p>
                    <ul className="list-unstyled d-flex flex-column gap-3 mb-0">
                        <li>
                            <i className="fa-solid fa-check me-2" style={{ color: "#e9a27a" }}></i>
                            Una propuesta por cliente, con cada línea trazada a sus actividades
                        </li>
                        <li>
                            <i className="fa-solid fa-check me-2" style={{ color: "#e9a27a" }}></i>
                            PDF para tu cliente y CSV para Holded, Quipu o tu gestoría
                        </li>
                        <li>
                            <i className="fa-solid fa-check me-2" style={{ color: "#e9a27a" }}></i>
                            Cada empresa ve solo sus datos
                        </li>
                    </ul>
                </div>

                <p className="small mb-0" style={{ color: "#9fb1c4" }}>
                    InvoiceOps prepara la facturación; la factura legal la emite tu programa de
                    facturas de siempre.
                </p>
            </section>

            <section className="io-auth-form">
                <div className="card io-auth-card">
                    <Outlet />
                </div>
            </section>
        </div>
    );
};