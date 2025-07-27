from flask import Flask, render_template, jsonify, request
from sensor_reader_module import get_sensor_data # นำเข้าฟังก์ชันอ่านเซ็นเซอร์
import json
import requests # นำเข้าไลบรารี requests สำหรับการเรียก API ภายนอก
import google.generativeai as genai # นำเข้าไลบรารี Gemini
from google.generativeai.types import BlockedPromptException # นำเข้า Exception ที่เกี่ยวข้องกับ Gemini

app = Flask(__name__)

# --- การตั้งค่า Gemini API ---
# สำคัญ: คุณต้องใส่ Gemini API Key ของคุณที่นี่
# หากคุณรันบน Raspberry Pi ของคุณเอง, การใส่ API Key ตรงๆ อาจจะทำได้
# แต่สำหรับ Production Environment แนะนำให้ใช้ Environment Variables เพื่อความปลอดภัย
# genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
genai.configure(api_key="") # <<< ใส่ API Key ของคุณที่นี่

# --- Route สำหรับหน้า Dashboard หลัก ---
@app.route('/')
def index():
    """แสดงผลหน้า HTML Dashboard หลัก"""
    return render_template('index.html')

# --- API Endpoint สำหรับดึงข้อมูลเซ็นเซอร์ ---
@app.route('/api/data')
def get_data():
    """
    ดึงข้อมูลเซ็นเซอร์โดยใช้ get_sensor_data และส่งคืนเป็น JSON.
    """
    print("\n--- Flask: Calling get_sensor_data() ---") # เพิ่ม Log
    sensor_data = get_sensor_data()
    print(f"--- Flask: Received from sensor_reader_module: {sensor_data}") # เพิ่ม Log
    return jsonify(sensor_data)

# --- API Endpoint สำหรับการวิเคราะห์โดย Gemini AI ---
@app.route('/api/ai', methods=['POST'])
def analyze_with_gemini():
    """
    รับคำถามและข้อมูลเซ็นเซอร์จาก Frontend,
    จากนั้นเรียก Gemini API เพื่อทำการวิเคราะห์.
    """
    data = request.json
    user_question = data.get('question', '')
    sensor_data = data.get('sensorData', {})

    # สร้างส่วนของ Prompt ที่เป็นบทบาทของ AI และข้อจำกัด
    ai_role_and_constraints = (
        "ตอนนี้คุณคือนักวิทยาศาสตร์ที่เชี่ยวชาญด้านดินและต้นไม้ที่สุดในโลก "
        "คุณสามารถให้คำแนะนำ user จากค่าแร่ธาตุในดินที่ถูกวัดเข้ามาดังนี้ "
        "Tempareture Huminity EC(ค่าการนำไฟฟ้า) PH Nitrogen Phosphorus และ Potassium "
        "โดยคุณต้องตอบคำถามที่ user ถามขึ้นมา ให้คำแนะนำ user จาก input ที่ได้รับจาก sensorNPK "
        "และตอบคำถามอย่างเป็นกันเองใช้คำศัพท์ที่ไม่ต้องวิชาการมากชิวๆ เหมือนเป็นเพื่อนคอยให้คำแนะนำ "
        "แต่ว่าถ้า user ถามเรื่องอื่นนอกจากเรื่องดินกับต้นไม้ คุณจะไม่สามารถตอบเรื่องนี้ได้ "
        "คุณสามารถตอบได้แค่ว่าขอโทษด้วยผมไม่สามารถช่วยคุณเรื่องนี้ได้"
    )

    # สร้างส่วนของ Prompt ที่เป็นข้อมูลเซ็นเซอร์
    sensor_info_for_prompt = (
        f"ข้อมูลสภาพดินปัจจุบัน:\n"
        f"- ความชื้น (Humidity): {sensor_data.get('humidity', '--')}%RH\n"
        f"- อุณหภูมิ (Temperature): {sensor_data.get('temperature', '--')}°C\n"
        f"- ความนำไฟฟ้า (EC): {sensor_data.get('ec', '--')} µS/cm\n"
        f"- ค่ากรด-ด่าง (pH): {sensor_data.get('ph', '--')}\n"
        f"- ไนโตรเจน (N): {sensor_data.get('nitrogen', '--')} mg/kg\n"
        f"- ฟอสฟอรัส (P): {sensor_data.get('phosphorus', '--')} mg/kg\n"
        f"- โพแทสเซียม (K): {sensor_data.get('potassium', '--')} mg/kg\n"
    )

    # รวม Prompt ทั้งหมด
    full_prompt = f"{ai_role_and_constraints}\n\n{sensor_info_for_prompt}\nคำถามจากผู้ใช้: {user_question}"

    try:
        print(f"\n--- Flask: Calling Gemini API with prompt (first 100 chars): {full_prompt[:100]}...") # เพิ่ม Log
        print(f"--- Flask: Full prompt length: {len(full_prompt)} characters.") # เพิ่ม Log
        
        # เรียก Gemini API จริงๆ
        model = genai.GenerativeModel('gemini-2.5-flash') # <<< แก้ไขตรงนี้: เปลี่ยนเป็น gemini-2.5-flash
        
        # เพิ่ม timeout ให้กับ generate_content call
        response = model.generate_content(full_prompt, request_options={'timeout': 60}) # เพิ่ม timeout 60 วินาที
        
        gemini_response_text = response.text
        print(f"--- Flask: Received response from Gemini (first 100 chars): {gemini_response_text[:100]}...") # เพิ่ม Log
        print(f"--- Flask: Gemini response length: {len(gemini_response_text)} characters.") # เพิ่ม Log

        return jsonify({"result": gemini_response_text})

    except BlockedPromptException as e:
        print(f"❌ เกิดข้อผิดพลาด Gemini API: Prompt ถูกบล็อก: {e}")
        return jsonify({"result": "ขออภัยครับ คำถามนี้ไม่สามารถประมวลผลได้เนื่องจากนโยบายด้านความปลอดภัยของ AI."}), 400
    except genai.APIError as e: # เปลี่ยนเป็น genai.APIError สำหรับข้อผิดพลาด API ทั่วไป
        print(f"❌ เกิดข้อผิดพลาด Gemini API: API Error: {e}")
        return jsonify({"result": "ขออภัยครับ มีปัญหาในการประมวลผลคำตอบจาก AI โปรดลองอีกครั้ง."}), 500
    except requests.exceptions.Timeout:
        print(f"❌ เกิดข้อผิดพลาด Gemini API: Request Timeout (เกิน {60} วินาที)")
        return jsonify({"result": "ขออภัยครับ การเชื่อมต่อกับ AI ใช้เวลานานเกินไป โปรดลองอีกครั้งหรือตรวจสอบการเชื่อมต่ออินเทอร์เน็ต."}), 504
    except requests.exceptions.ConnectionError as e:
        print(f"❌ เกิดข้อผิดพลาด Gemini API: Connection Error: {e}")
        return jsonify({"result": "ขออภัยครับ ไม่สามารถเชื่อมต่อกับ AI ได้ โปรดตรวจสอบการเชื่อมต่ออินเทอร์เน็ต."}), 503
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิดในการเรียก Gemini API: {e}")
        # หากเกิดข้อผิดพลาดในการเรียก API, ให้ตอบกลับด้วยข้อความแจ้งข้อผิดพลาด
        return jsonify({"result": f"เกิดข้อผิดพลาดในการวิเคราะห์โดย Gemini AI: {e}"}), 500

if __name__ == '__main__':
    # Flask จะให้บริการบนทุก IP ที่พอร์ต 5000
    # คุณสามารถเข้าถึงได้จากเบราว์เซอร์โดยใช้ http://YOUR_PI_IP_ADDRESS:5000
    app.run(host='0.0.0.0', port=5000)
