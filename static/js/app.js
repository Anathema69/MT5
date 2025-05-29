document.addEventListener("DOMContentLoaded", () => {
  // Lista completa de FOREX
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
  };
  const assetRadios = document.getElementsByName("asset_type");
  const symbolSelect = document.getElementById("symbol");
  const otherContainer = document.getElementById("other-container");
  const otherInput = document.getElementById("symbol_other");

  // Función para poblar los símbolos
  function populateSymbols(type) {
    symbolSelect.innerHTML = "";
    symbols[type].forEach(sym => {
      const opt = document.createElement("option");
      opt.value = sym;
      opt.textContent = sym;
      symbolSelect.appendChild(opt);
    });
    // siempre agregar “Otro…”
    const optOther = document.createElement("option");
    optOther.value = "other";
    optOther.textContent = "Otro…";
    symbolSelect.appendChild(optOther);
    // oculta input de otro
    otherContainer.style.display = "none";
    otherInput.value = "";
    otherInput.required = false;
  }

  // Al cambiar tipo de activo
  assetRadios.forEach(radio => {
    radio.addEventListener("change", () => {
      if (radio.checked) populateSymbols(radio.value);
    });
  });

  // Al cambiar selección de símbolo (para “Otro…”)
  symbolSelect.addEventListener("change", () => {
    if (symbolSelect.value === "other") {
      otherContainer.style.display = "block";
      otherInput.required = true;
    } else {
      otherContainer.style.display = "none";
      otherInput.required = false;
      otherInput.value = "";
    }
  });

  // Init: carga divisas (forex) por defecto
  const defaultType = document.querySelector('input[name="asset_type"]:checked').value;
  populateSymbols(defaultType);

  // Intercepta el envío del form para manejar la descarga por fetch()
const downloadForm = document.getElementById('download-form');
if (downloadForm) {
  downloadForm.addEventListener('submit', async e => {
    e.preventDefault();
    const loader = document.getElementById('loader');
    loader.style.display = 'flex';

    const formData = new FormData(downloadForm);
    try {
      const resp = await fetch(downloadForm.action, {
        method: downloadForm.method,
        body: formData
      });
      if (!resp.ok) throw new Error(`Error ${resp.status}`);

      // Extrae filename de Content-Disposition
      const cd = resp.headers.get('Content-Disposition') || '';
      const m  = cd.match(/filename="?(.+?)"?$/);
      const filename = m ? m[1] : 'data.csv';

      // Descarga el blob
      const blob = await resp.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

    } catch (err) {
      alert(err);
    } finally {
      loader.style.display = 'none';
    }
  });
}


});
