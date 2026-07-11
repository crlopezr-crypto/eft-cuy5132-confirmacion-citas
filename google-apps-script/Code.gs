const SHEET_NAME = "Hoja 1";

function doGet(e) {
  const action = e.parameter.action;
  const extension = e.parameter.extension;
  const sheet = SpreadsheetApp.getActiveSpreadsheet()
                              .getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();

  if (action === "getCita") {
    for (let i = 1; i < data.length; i++) {
     if (String(data[i][1]).trim() === String(extension).trim()) {
        
        // Formatear fecha
        const fechaRaw = data[i][4];
        const fecha = fechaRaw instanceof Date 
          ? Utilities.formatDate(fechaRaw, "America/Santiago", "yyyy-MM-dd")
          : String(fechaRaw);

        // Formatear hora
        const horaRaw = data[i][5];
        const hora = horaRaw instanceof Date
          ? Utilities.formatDate(horaRaw, "America/Santiago", "HH:mm")
          : String(horaRaw);

        return ContentService.createTextOutput(JSON.stringify({
          id:           data[i][0],
          extension:    data[i][1],
          paciente:     data[i][2],
          especialidad: data[i][3],
          fecha:        fecha,
          hora:         hora,
          estado:       data[i][6]
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }
    return ContentService.createTextOutput(JSON.stringify({error: "No encontrada"}))
                         .setMimeType(ContentService.MimeType.JSON);
  }

  return ContentService.createTextOutput(JSON.stringify({error: "Acción no válida"}))
                       .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  const body = JSON.parse(e.postData.contents);
  const action = body.action;
  const sheet = SpreadsheetApp.getActiveSpreadsheet()
                              .getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();

  if (action === "updateCita") {
    const id = String(body.id);
    const estado = body.estado;

    for (let i = 1; i < data.length; i++) {
      if (String(data[i][0]) === id) {
        sheet.getRange(i + 1, 7).setValue(estado);
        return ContentService.createTextOutput(JSON.stringify({success: true}))
                             .setMimeType(ContentService.MimeType.JSON);
      }
    }
  }

  return ContentService.createTextOutput(JSON.stringify({error: "No actualizado"}))
                       .setMimeType(ContentService.MimeType.JSON);
}
