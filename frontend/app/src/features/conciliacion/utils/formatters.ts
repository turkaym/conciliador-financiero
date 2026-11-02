export const formatearMonedaSegura = (monto: string | number | undefined | null, moneda?: string | null) => {
  if (monto === undefined || monto === null) return "$ 0,00";
  let currencyCode = "ARS";
  if (moneda && typeof moneda === 'string') {
     if (moneda.toUpperCase().includes("USD")) currencyCode = "USD";
     else if (moneda.toUpperCase().includes("ARS")) currencyCode = "ARS";
  }
  const val = Number(monto) || 0;
  try {
    return new Intl.NumberFormat("es-AR", { style: "currency", currency: currencyCode }).format(val);
  } catch (e) {
    return `$ ${val.toFixed(2)}`;
  }
};

export const formatFechaUI = (fechaStr?: string | null) => {
  if (!fechaStr) return "S/D";
  try {
    const [year, month, day] = fechaStr.split("-");
    return `${day}/${month}/${year}`;
  } catch (e) {
    return fechaStr;
  }
};