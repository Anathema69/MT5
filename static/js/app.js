// static/js/app.js
document.addEventListener("DOMContentLoaded", () => {
  // 1) Datos de símbolos e intervalos
  const symbols = {
    // Lista exacta de sintéticos tal como aparece en la imagen adjunta
    synthetic: [
      "SFX Vol 20","SFX Vol 40","SFX Vol 60","SFX Vol 80","SFX Vol 99",
      "FlipX 1","FlipX 2","FlipX 3","FlipX 4","FlipX 5",
      "PainX 400","PainX 600","PainX 800","PainX 999","PainX 1200",
      "GainX 400","GainX 600","GainX 800","GainX 999","GainX 1200"
    ],

    // Opciones Forex sin cambios
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

  // 2) Inicializar Tom Select para el Símbolo
  const symbolSelect = new TomSelect("#symbol-select", {
    maxItems: 1,
    create: false,
    placeholder: "Escribe o busca.",
    onInitialize() {
      // Al cargar, inyectamos la lista de 'synthetic' (porque por defecto el radio está en 'Sintéticos')
      const opts = symbols.synthetic.map(s => ({ value: s, text: s }));
      this.clearOptions();
      this.addOption(opts);
      // Preseleccionamos el primer sintetico:
      this.setValue(opts[0].value);

      // Cuando el usuario cambie el tipo de activo (radio), recargamos la lista:
      document.querySelectorAll('input[name="asset_type"]').forEach(radio => {
        radio.addEventListener("change", () => {
          const arr = symbols[radio.value]; // 'forex' o 'synthetic'
          const newOpts = arr.map(s => ({ value: s, text: s }));
          this.clearOptions();
          this.addOption(newOpts);
          // Seleccionamos automáticamente el primero de la nueva lista:
          this.setValue(newOpts[0].value);
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

  // 4) Flatpickr en inputs de fecha (toma el "value" que viene en el HTML)
  flatpickr("#start-date", {
    dateFormat: "Y-m-d",
    allowInput: true
    // No hace falta defaultDate porque el <input> ya trae value="{{ default_start }}"
  });
  flatpickr("#end-date", {
    dateFormat: "Y-m-d",
    allowInput: true
    // El <input> trae value="{{ default_end }}"
  });

  // 5) Manejo del formulario + spinner (igual que antes)
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
