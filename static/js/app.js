// app.js
document.addEventListener("DOMContentLoaded", () => {
  // 1) Datos de símbolos e intervalos
  const symbols = {
    synthetic: ["gainx400", "gainx600"],
    forex: [
      "AUDCAD","AUDCHF","AUDJPY","AUDNZD","AUDUSD",
      "CADCHF","CADJPY","CHFJPY",
      "EURAUD","EURCAD","EURCHF","EURGBP","EURHUF","EURJPY","EURNOK","EURNZD","EURPLN","EURSEK","EURSGD","EURTRY","EURUSD","EURZAR",
      "GBPAUD","GBPCAD","GBPCHF","GBPJPY","GBPNZD","GBPSEK","GBPUSD",
      "NZDCAD","NZDCHF","NZDJPY","NZDUSD",
      "TRYJPY",
      "USDCAD","USDCHF","USDCNH","USDHKD","USDHUF","USDJPY","USDMXN","USDNOK","USDPLN","USDSEK","USDSGD","USDTRY","USDZAR"
    ]
  }; // :contentReference[oaicite:0]{index=0}

  const intervals = [
    ["M1",  "1 Minuto"], ["M2",  "2 Minutos"], ["M3",  "3 Minutos"],
    ["M4",  "4 Minutos"], ["M5",  "5 Minutos"], ["M6",  "6 Minutos"],
    ["M10", "10 Minutos"],["M12", "12 Minutos"],["M15", "15 Minutos"],
    ["M20", "20 Minutos"],["M30", "30 Minutos"],
    ["H1",  "1 Hora"],   ["H2",  "2 Horas"],   ["H3",  "3 Horas"],
    ["H4",  "4 Horas"],  ["H6",  "6 Horas"],   ["H8",  "8 Horas"],
    ["H12", "12 Horas"], ["D1",  "Diario"],    ["W1",  "Semanal"],
    ["MN1", "Mensual"]
  ]; // :contentReference[oaicite:1]{index=1}

  // 2) Inicializar Tom Select para el Símbolo
  const symbolSelect = new TomSelect("#symbol-select", {
    options: symbols.forex.map(s => ({ value: s, text: s })),
    maxItems: 1,
    create: false,
    placeholder: "Escribe o busca.",
    onInitialize() {
      // Al cambiar el tipo de activo, recargamos las opciones
      document.querySelectorAll('input[name="asset_type"]').forEach(radio => {
        radio.addEventListener("change", () => {
          const opts = symbols[radio.value].map(s => ({ value: s, text: s }));
          this.clearOptions();
          this.addOptions(opts);
          this.clear(true);
        });
      });
    }
  });

  // 3) Inicializar Tom Select para el Intervalo
  const intervalSelect = new TomSelect("#interval-select", {
    options: intervals.map(([value, text]) => ({ value, text })),
    maxItems: 1,
    create: false,
    placeholder: "Selecciona intervalo"
  });

  // 4) Flatpickr en inputs de fecha
  flatpickr("#start-date", {
    dateFormat: "Y-m-d",
    allowInput: true
  });
  flatpickr("#end-date", {
    dateFormat: "Y-m-d",
    allowInput: true
  });

  // 5) Manejo del formulario + spinner
  const form = document.getElementById("download-form");
  const loader = document.getElementById("loader");

  form.addEventListener("submit", async e => {
    e.preventDefault();
    loader.style.display = "flex";

    const formData = new FormData(form);
    try {
      const resp = await fetch(form.action, {
        method: form.method,
        body: formData
      });
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      const disposition = resp.headers.get("Content-Disposition") || "";
      const filenameMatch = disposition.match(/filename="?(.+?)"?$/);
      const filename = filenameMatch ? filenameMatch[1] : "data.csv";
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err);
    } finally {
      loader.style.display = "none";
    }
  });
});
