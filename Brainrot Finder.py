import cv2
import numpy as np
import pytesseract
import pyttsx3
import re
import win32gui, win32ui, win32con, win32api 
import ctypes
import pydirectinput 
import time         
from fuzzywuzzy import process
from colorama import Fore, Style, init

# Initialize color text for console
init()

# --- NEW: Initialize Voice Engine ---
engine = pyttsx3.init()
engine.setProperty('rate', 150) 

# --- CONFIGURATION ---
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Update this path if necessary, Install Tesseract OCR from: https://github.com/AlexanderP/tesseract-appimage/releases

# How long to hold 'E' to ensure the purchase happens
BUY_HOLD_DURATION = 3.5 

# The list of Brainrots you want to be brought 
RARE_BRAINROTS = [
    "Strawberry Elephant", "Dragon Cannelloni", "Spaghetti Tualetti",
    "Nuclearo Dinosauro", "Los Bros", "Chicleteira Bicicleteira",
    "Trulimero Trulicina" 
]

# Common ones to recognize
COMMON_BRAINROTS = [
    "Noobini Pizzanini", "Fluriflura", "Perochello Lemonchello", 
    "Tim Cheese", "Lirili Larila", "Racooni Jandelini"
]

# --- DIMENSIONS ---
SCAN_BOX_WIDTH = 900
SCAN_BOX_HEIGHT = 560
# The smaller the window or diemnsions are, the less accurate OCR will be.

def process_image(img):
    """
    Filters for BRIGHT WHITE text to ignore the game background.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_white = np.array([0, 0, 180])
    upper_white = np.array([180, 50, 255])
    mask = cv2.inRange(hsv, lower_white, upper_white)
    kernel = np.ones((2,2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    result = cv2.bitwise_not(mask)
    return result

def get_roblox_window():
    """Finds the Roblox window handle (HWND)."""
    try:
        hwnd = win32gui.FindWindow(None, "Roblox")
        if hwnd and win32gui.IsWindow(hwnd):
            return hwnd
    except:
        pass
    return None

def capture_background_window(hwnd):
    """Captures a specific window in the background (like OBS)."""
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        if width < 10 or height < 10:
            return None

        wDC = win32gui.GetWindowDC(hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, width, height)
        cDC.SelectObject(dataBitMap)

        result = ctypes.windll.user32.PrintWindow(hwnd, cDC.GetSafeHdc(), 2)

        if result != 1:
            return None 

        signedIntsArray = dataBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (height, width, 4) 

        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    except Exception as e:
        return None

def main():
    print(f"{Fore.CYAN}--- Brainrot Scanner Active (Auto-Buy Mode) ---{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Press Ctrl+C to stop.{Style.RESET_ALL}")
    
    hwnd = None
    while not hwnd:
        hwnd = get_roblox_window()
        if not hwnd:
            time.sleep(1)
            print("Waiting for 'Roblox' window...", end='\r')
    
    print(f"\n{Fore.GREEN}Latched onto 'Roblox'!{Style.RESET_ALL}")
    
    try:
        while True:
            screenshot = capture_background_window(hwnd)
            
            if screenshot is None:
                hwnd = get_roblox_window()
                continue

            h, w, _ = screenshot.shape
            start_y = int((h / 2) - (SCAN_BOX_HEIGHT / 2)) - 100
            start_x = int((w / 2) - (SCAN_BOX_WIDTH / 2))
            
            if start_y < 0: start_y = 0
            if start_x < 0: start_x = 0
            
            cropped_img = screenshot[start_y:start_y+SCAN_BOX_HEIGHT, start_x:start_x+SCAN_BOX_WIDTH]
            processed_img = process_image(cropped_img)
            text = pytesseract.image_to_string(processed_img, config='--psm 6').strip()

            # Clean text
            clean_text = re.sub(r'[^a-zA-Z\s]', '', text)
            clean_text = re.sub(r'\b\w\b', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

            if len(clean_text) > 4: 
                best_match, score = process.extractOne(clean_text, RARE_BRAINROTS)

                if score > 85: 
                    print(f"{Fore.RED}!!! FOUND RARE: {best_match} !!!{Style.RESET_ALL}")
                    engine.say(f"Buying {best_match}")
                    
                    # --- AUTO BUY LOGIC ---
                    try:
                        print(f"{Fore.GREEN}>>> ACTIVATING WINDOW TO BUY <<<{Style.RESET_ALL}")
                        
                        # 1. Force Focus the window
                        # (We press Alt just in case Windows blocks the focus switch)
                        win32api.keybd_event(0x12, 0, 0, 0) # Alt Down
                        win32gui.SetForegroundWindow(hwnd)
                        win32api.keybd_event(0x12, 0, 2, 0) # Alt Up
                        
                        # Give it a split second to pop up
                        time.sleep(0.2)
                        
                        # 2. Hold E
                        pydirectinput.keyDown('e')
                        time.sleep(BUY_HOLD_DURATION)
                        pydirectinput.keyUp('e')
                        
                        print("Purchase complete. Resuming scan...")
                        
                    except Exception as e:
                        print(f"Could not auto-buy: {e}")

                    engine.runAndWait()
                
                else:
                    common_match, common_score = process.extractOne(clean_text, COMMON_BRAINROTS)
                    if common_score > 85:
                        print(f"{Fore.LIGHTBLACK_EX}Saw: {common_match} (Ignored){Style.RESET_ALL}")
                    else:
                        print(f"{Fore.LIGHTBLACK_EX}Reading: {clean_text}{Style.RESET_ALL}")
            
    except KeyboardInterrupt:
        print(f"\n{Fore.CYAN}Scanner stopped.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
