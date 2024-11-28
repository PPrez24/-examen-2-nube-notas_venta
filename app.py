from flask import Flask, request, jsonify
import pymysql
import boto3
from fpdf import FPDF
import os
import botocore.exceptions

app = Flask(__name__)

# Configuración de base de datos y AWS
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")
s3_bucket = os.getenv("S3_BUCKET")
aws_region = os.getenv("AWS_REGION")
NOTIFICACIONES_URL = "http://54.221.150.143:5002"

# Inicializar conexión a la base de datos
db = pymysql.connect(
    host=db_host,
    user=db_user,
    password=db_password,
    db=db_name
)

# Inicializar clientes de AWS
s3 = boto3.client('s3', region_name=aws_region)
sns = boto3.client('sns', region_name=aws_region)

@app.route('/notas_venta', methods=['POST'])
def crear_nota_venta():
    data = request.json
    if not data.get('Cliente_ID') or not data.get('Direccion_Facturacion') or not data.get('Total_Nota'):
        return jsonify({'error': 'Cliente, Dirección de Facturación y Total son requeridos'}), 400
    cursor = db.cursor()

    try:
        # Insertar nota de venta
        consulta = """
            INSERT INTO NotasVenta (Cliente_ID, Direccion_Facturacion, Direccion_Envio, Total_Nota)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(consulta, (data['Cliente_ID'], data['Direccion_Facturacion'], data.get('Direccion_Envio'), data['Total_Nota']))
        id_nota = cursor.lastrowid

        # Insertar contenido de la nota
        for item in data.get('Contenido', []):
            consulta_contenido = """
                INSERT INTO ContenidoNotas (Nota_ID, Producto_ID, Cantidad, Precio_Unitario, Importe)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(consulta_contenido, (id_nota, item['Producto_ID'], item['Cantidad'], item['Precio_Unitario'], item['Importe']))

        db.commit()

        # Generar PDF
        archivo_pdf = generar_pdf(id_nota, data)
        subir_a_s3(archivo_pdf)

        # Llamar al módulo Notificaciones
        notificacion_payload = {
            "correo": data.get('Correo_Electronico'),
            "mensaje": f"Tu nota de venta #{id_nota} ha sido creada exitosamente."
        }
        response = requests.post(f"{NOTIFICACIONES_URL}/notificaciones", json=notificacion_payload)
        response.raise_for_status()

        return jsonify({'mensaje': 'Nota de venta creada y notificación enviada exitosamente'}), 201

    except botocore.exceptions.NoCredentialsError:
        return jsonify({'error': 'Credenciales de AWS no configuradas correctamente'}), 500
    except botocore.exceptions.ClientError as e:
        return jsonify({'error': f"Error al interactuar con AWS: {str(e)}"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Error al enviar la notificación', 'detalle': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generar_pdf(id_nota, data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Nota de Venta ID: {id_nota}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Cliente: {data['Cliente_ID']}", ln=True)
    pdf.cell(200, 10, txt=f"Dirección Facturación: {data['Direccion_Facturacion']}", ln=True)
    pdf.cell(200, 10, txt=f"Dirección Envío: {data.get('Direccion_Envio', '')}", ln=True)
    pdf.cell(200, 10, txt=f"Total Nota: {data['Total_Nota']}", ln=True)
    for item in data.get('Contenido', []):
        pdf.cell(200, 10, txt=f"Producto: {item['Producto_ID']} - Cantidad: {item['Cantidad']} - Precio: {item['Precio_Unitario']} - Importe: {item['Importe']}", ln=True)

    nombre_archivo = f"nota_venta_{id_nota}.pdf"
    pdf.output(nombre_archivo)
    return nombre_archivo

def subir_a_s3(nombre_archivo):
    try:
        s3.upload_file(nombre_archivo, s3_bucket, nombre_archivo)
    except botocore.exceptions.ClientError as e:
        raise Exception(f"Error al subir archivo a S3: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
