// static/js/app.js
document.addEventListener("DOMContentLoaded", () => {
  // 1) Datos de símbolos e intervalos
  const symbols = {
    synthetic: [
      "SFX Vol 20",  "SFX Vol 40",  "SFX Vol 60",  "SFX Vol 80",  "SFX Vol 99",
      "FlipX 1",     "FlipX 2",     "FlipX 3",     "FlipX 4",     "FlipX 5",
      "PainX 400",   "PainX 600",   "PainX 800",   "PainX 999",   "PainX 1200",
      "GainX 400",   "GainX 600",   "GainX 800",   "GainX 999",   "GainX 1200"
    ],
    forex: [
      "AUDCAD","AUDCHF","AUDJPY","AUDNZD","AUDUSD",
      "CADCHF","CADJPY","CHFJPY",
      "EURAUD","EURCAD","EURCHF","EURGBP","EURHUF","EURJPY","EURNOK","EURNZD","EURPLN","EURSEK","EURSGD","EURTRY","EURUSD","EURZAR",
      "GBPAUD","GBPCAD","GBPCHF","GBPJPY","GBPNZD","GBPSEK","GBPUSD",
      "NZDCAD","NZDCHF","NZDJPY","NZDUSD",
      "TRYJPY",
      "USDCAD","USDCHF","USDCNH","USDHKD","USDHUF","USDJPY","USDMXN","USDNOK","USDPLN","USDSEK","USDSGD","USDTRY","USDZAR"
    ]
  };

  const intervals = [
    ["M1",  "1 Minuto"], ["M2",  "2 Minutos"], ["M3",  "3 Minutos"],
    ["M4",  "4 Minutos"], ["M5",  "5 Minutos"], ["M6",  "6 Minutos"],
    ["M10", "10 Minutos"],["M12", "12 Minutos"],["M15", "15 Minutos"],
    ["M20", "20 Minutos"],["M30", "30 Minutos"],
    ["H1",  "1 Hora"],   ["H2",  "2 Horas"],   ["H3",  "3 Horas"],
    ["H4",  "4 Horas"],  ["H6",  "6 Horas"],   ["H8",  "8 Horas"],
    ["H12", "12 Horas"], ["D1",  "Diario"],    ["W1",  "Semanal"],
    ["MN1", "Mensual"]
  ];

  // Referencia al contenedor del checkbox
  const ticksContainer = document.getElementById("ticks-container");
  const ticksCheckbox = document.getElementById("download-ticks");

  // 2) Inicializar Tom Select para el Símbolo
  const symbolSelect = new TomSelect("#symbol-select", {
    maxItems: 1,
    create: false,
    placeholder: "Escribe o busca.",
    onInitialize() {
      // a) Al cargar la página, el radio “Sintéticos” está chequeado por defecto:
      const initialArr = symbols.synthetic;
      const opts = initialArr.map(s => ({ value: s, text: s }));
      this.clearOptions();
      this.addOption(opts);
      this.setValue(opts[0].value); // Preseleccionar primer sintetico

      // b) Listener: cuando cambie el radio de tipo de activo, recargamos la lista
      document.querySelectorAll('input[name="asset_type"]').forEach(radio => {
        radio.addEventListener("change", () => {
          // 1. Cargar la lista de símbolos adecuada
          const arr = symbols[radio.value]; // “forex” o “synthetic”
          const newOpts = arr.map(s => ({ value: s, text: s }));
          this.clearOptions();
          this.addOption(newOpts);
          this.setValue(newOpts[0].value);

          // 2. Ocultar o mostrar el checkbox “Descargar Ticks”
          if (radio.value === "forex") {
            // Ocultamos el contenedor completo
            ticksContainer.style.display = "none";
            // Resetear el valor del checkbox a 'false'
            ticksCheckbox.checked = false;
          } else {
            // “synthetic”: mostramos el contenedor (pero el checkbox inicia desmarcado)
            ticksContainer.style.display = "block";
            ticksCheckbox.checked = false;
          }
        });
      });
    }
  });

  // 3) Inicializar Tom Select para el Intervalo
  const intervalSelect = new TomSelect("#interval-select", {
    options: intervals.map(([value, text]) => ({ value, text })),
    maxItems: 1,
    create: false,
    placeholder: "Selecciona intervalo",
    onInitialize() {
      // Preseleccionamos el primer intervalo (“M1”)
      this.setValue(intervals[0][0]);
    }
  });

  // 4) Flatpickr en inputs de fecha (toman el value="{{ default_start }}"/"{{ default_end }}")
  flatpickr("#start-date", {
    dateFormat: "Y-m-d",
    allowInput: true
  });
  flatpickr("#end-date", {
    dateFormat: "Y-m-d",
    allowInput: true
  });

  // 5) Al cargar la página, comprobamos qué radio está marcado para ocultar/mostrar el checkbox
  const initialAsset = document.querySelector('input[name="asset_type"]:checked').value;
  if (initialAsset === "forex") {
    ticksContainer.style.display = "none";
    ticksCheckbox.checked = false;
  } else {
    ticksContainer.style.display = "block";
    ticksCheckbox.checked = false;
  }

  // 6) Manejo del formulario + spinner (igual que antes)
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
      const filename = filenameMatch ? filenameMatch[1] : "data";
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
