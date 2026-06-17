import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_pdf_matrix(user_id: int, name: str, destiny: int, matrix_text: str) -> bytes:
    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        c.setFont("Helvetica-Bold", 16)
        c.drawString(30, height - 30, f"Матрица судьбы для {name}")
        c.setFont("Helvetica", 12)
        c.drawString(30, height - 50, f"Число судьбы: {destiny}")
        c.drawString(30, height - 70, f"Дата формирования: {datetime.datetime.now().strftime('%d.%m.%Y')}")
        y = height - 100
        for line in matrix_text.split('\n'):
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 12)
            if len(line) > 80:
                for i in range(0, len(line), 80):
                    c.drawString(30, y, line[i:i+80])
                    y -= 15
            else:
                c.drawString(30, y, line)
                y -= 15
        c.save()
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        print(f"Ошибка генерации PDF: {e}")
        return None