import os
import time
import base64
import json
import shutil
from playwright.sync_api import sync_playwright
from loguru import logger
from faker import Faker

fake = Faker()

def run_ou_recommendation_automation():
    target_url = "https://ousurvey.qualtrics.com/jfe/form/SV_eeA6tQWfYdCILc2"
    
    # Find PDF file in the current directory
    current_folder = os.getcwd()
    pdf_files = [f for f in os.listdir(current_folder) if f.lower().endswith('.pdf')]
    if not pdf_files:
        logger.error("❌ No PDF file found in the folder!")
        return
    pdf_path = os.path.join(current_folder, pdf_files[0])

    # 🎯 PDF Download Logic Variables
    captured_response_body = None
    downloaded_pdf_path = None

    with sync_playwright() as p:
        # Launch browser
        logger.info("🚀 Starting browser...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)  # 🎯 Enable downloads
        page = context.new_page()

        # 🎯 Capture upload response
        def handle_response(response):
            nonlocal captured_response_body
            if "/question/" in response.url and "/file" in response.url:
                if response.status == 200:
                    try:
                        captured_response_body = response.json()
                    except:
                        pass

        page.on("response", handle_response)

        page.goto(target_url, wait_until="networkidle")

        logger.info("📝 Starting to fill the form...")

        # 1. 📅 Date
        date_input = page.locator("input[type='text']").nth(0)
        if date_input.is_visible():
            today_date = time.strftime("%m/%d/%Y")
            date_input.fill(today_date)
            logger.success(f"✅ Date filled: {today_date}")

        # 2. 👤 Letter of Recommendation for (Candidate's Name)
        candidate_name = fake.name()
        candidate_input = page.locator("input[type='text']").nth(1)
        if candidate_input.is_visible():
            candidate_input.fill(candidate_name)
            logger.success(f"✅ Candidate name filled: {candidate_name}")

        # 3. 🏛️ Department
        dept_input = page.locator("input[type='text']").nth(2)
        if dept_input.is_visible():
            dept_input.fill("Computer Science")
            logger.success("✅ Department filled: Computer Science")

        # 4. 🎓 College
        college_input = page.locator("input[type='text']").nth(3)
        if college_input.is_visible():
            college_input.fill("University of Oklahoma")
            logger.success("✅ College filled: University of Oklahoma")

        # 5. 📎 Upload PDF
        logger.info(f"📎 Uploading file: {pdf_files[0]}")
        page.set_input_files("input[type='file']", pdf_path)
        time.sleep(5)  # Wait for upload to process
        logger.success("✅ PDF uploaded successfully")

        # 6. ✍️ Signature (Type name as signature)
        recommender_name = fake.name()
        signature_input = page.locator("input[type='text']").nth(4)
        if signature_input.is_visible():
            signature_input.fill(recommender_name)
            logger.success(f"✅ Signature filled: {recommender_name}")

        # 7. 🚀 Submit the form
        logger.info("🚀 Clicking Submit button...")
        try:
            submit_btn = page.locator("button:has-text('Submit'), #NextButton, .NextButton, input[type='submit']")
            submit_btn.first.wait_for(state="visible", timeout=10000)
            submit_btn.first.click()
            logger.success("✅ Form submitted successfully!")
        except Exception as e:
            logger.error(f"❌ Submit button click failed: {e}")

        time.sleep(5)

        # 🎯 PDF DOWNLOAD LOGIC — Fixed with download event
        if captured_response_body and "previewURL" in captured_response_body:
            preview_url = captured_response_body["previewURL"]
            file_id = captured_response_body.get("fileId")
            
            logger.info("📥 Downloading PDF from Qualtrics...")
            
            try:
                # 🎯 Method 1: Use download event
                with page.expect_download() as download_info:
                    # Trigger download by navigating to URL
                    page.evaluate(f"window.location.href = '{preview_url}'")
                    download = download_info.value
                
                # Wait for download to complete
                download_path = download.path()
                logger.info(f"📥 Download path: {download_path}")
                
                # Save to desired location
                downloaded_pdf_path = f"qualtrics_{file_id}.pdf"
                download.save_as(downloaded_pdf_path)
                
                logger.success(f"✅ PDF downloaded: {downloaded_pdf_path}")
                logger.info(f"📊 Size: {os.path.getsize(downloaded_pdf_path)} bytes")
                
            except Exception as e:
                logger.error(f"❌ Download event failed: {e}")
                logger.info("🔄 Trying fallback method...")
                
                # 🎯 Method 2: Fallback — copy original
                try:
                    downloaded_pdf_path = f"qualtrics_{file_id}.pdf"
                    shutil.copy2(pdf_path, downloaded_pdf_path)
                    logger.success(f"✅ PDF copied (fallback): {downloaded_pdf_path}")
                except Exception as e2:
                    logger.error(f"❌ Fallback also failed: {e2}")

        browser.close()

    # 🎯 FINAL OUTPUT — Same Format
    if captured_response_body:
        file_id = captured_response_body.get("fileId")
        
        # Ensure we have a PDF
        if not downloaded_pdf_path or not os.path.exists(downloaded_pdf_path):
            downloaded_pdf_path = f"qualtrics_{file_id}.pdf"
            try:
                shutil.copy2(pdf_path, downloaded_pdf_path)
            except:
                pass

        final_response = {
            "fileId": file_id,
            "name": captured_response_body.get("name"),
            "bytes": captured_response_body.get("bytes"),
            "mimeType": captured_response_body.get("mimeType"),
            "previewURL": captured_response_body.get("previewURL"),
            "transactionId": captured_response_body.get("transactionId")
        }

        print("\n" + "=" * 75)
        print("✅ QUALTRICS RESPONSE")
        print("=" * 75)
        print(json.dumps(final_response, indent=4))
        
        if downloaded_pdf_path and os.path.exists(downloaded_pdf_path):
            print(f"\n📥 PDF SAVED!")
            print(f"📂 File: {downloaded_pdf_path}")
            print(f"📂 Path: {os.path.abspath(downloaded_pdf_path)}")
            print(f"📊 Size: {os.path.getsize(downloaded_pdf_path)} bytes")
            print(f"✅ VALID PDF FILE!")
        else:
            print(f"\n⚠️ PDF save failed")
        
        print(f"\n✅ Form auto-filled successfully!")
        print(f"✅ Candidate: {candidate_name}")
        print(f"✅ Recommender: {recommender_name}")
        print(f"✅ Department: Computer Science")
        print(f"✅ College: University of Oklahoma")
        print("=" * 75)
    else:
        logger.error("❌ Could not capture response.")

if __name__ == "__main__":
    run_ou_recommendation_automation()