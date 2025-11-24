"""
QR code generator for tables to redirect the user/waiter to the table endpoint
"""
import sys
import os

# Add backend directory to sys.path to allow running as script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask
from src.core.i18n_logger import get_i18n_logger
from config import LANG

logger = get_i18n_logger(__name__)

def generate_table_qr_code(endpoint: str, table_id: int, save_path: str):

    """
    Generate a QR code for a table.
    
    Args:
        endpoint: The endpoint to encode in the QR code
        table_id: The ID of the table
        save_path: The path to save the QR code image
    """

    try :
        qr = qrcode.QRCode(
            version= None, # The version parameter is an integer from 1 to 40 that controls the size of the QR Code (the smallest, version 1, is a 21x21 matrix). Set to None and use the fit parameter when making the code to determine this automatically.
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,

        )

        # Combine Wi-Fi data with the endpoint URL
        qr_data = f"URL:{endpoint}?table_id={table_id}"
    
        qr.add_data(qr_data)
        
        qr.make(fit=True)

        # First generate a temporary QR so we know its size
        base_img = qr.make_image(
            fill_color='black',
            back_color='white',
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            color_mask=RadialGradiantColorMask(),
        ).convert("RGB")

        qr_w, qr_h = base_img.size

        # ------------------------------
        # Auto-size number image
        # ------------------------------
        embed_size = int(qr_w * 0.25)
        
        # Create a transparent image for the number with rounded corners
        num_img = Image.new("RGBA", (embed_size, embed_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(num_img)
        
        # Draw rounded white rectangle background
        # Leave a small margin for the border effect if needed, or fill it
        rect_margin = 0
        draw.rounded_rectangle(
            (rect_margin, rect_margin, embed_size - rect_margin, embed_size - rect_margin),
            radius=int(embed_size * 0.2), # 20% radius
            fill="white",
            outline="blue",
            width=2
        )

        text = str(table_id)
        
        # Dynamic Font Sizing
        # Start with a font size close to the embed size
        font_size = int(embed_size * 0.8) 
        font = None
        
        while font_size > 5:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
                break # Default font doesn't scale well, so we stop if we can't load arial
            
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Check if it fits with some padding (e.g. 80% of the box)
            if text_width <= embed_size * 0.7 and text_height <= embed_size * 0.7:
                break
            
            font_size -= 2
            
        # If we fell back to default font or loop finished
        if font is None:
             font = ImageFont.load_default()

        # Recalculate final bbox to center it
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Draw text centered
        draw.text(
            ((embed_size - text_width) / 2, (embed_size - text_height) / 2 - bbox[1]), # Adjust for vertical alignment
            text,
            fill="black",
            font=font,
        )

        # -----------------------------------------------------
        # 🔵 Create final QR with the auto-sized number image
        # -----------------------------------------------------
        final_img = qr.make_image(
            fill_color='black',
            back_color='white',
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            color_mask=RadialGradiantColorMask(),
            embedded_image=num_img,
        )

        os.makedirs(save_path, exist_ok=True)
        final_img.save(os.path.join(save_path, f"table_{table_id}.png"))
        logger.info(
                "table.qrcode.created",
                language=LANG,
                table_id=table_id
            )
    except Exception as e:
        logger.error(
                "table.qrcode.error",
                language=LANG,
                table_id=table_id,
                error=str(e)
            )
        return False
        
    return True


def generate_qr_code_for_tables(endpoint: str, tables: list[int], save_path: str):
    """
    Generate a QR code for a table.
    
    Args:
        endpoint: The endpoint to encode in the QR code 
        tables: The list of tables ids to generate QR codes for
        save_path: The path to save the QR code image
    """
    for table_id in tables:
        generate_table_qr_code(endpoint, table_id, save_path)


def make_rounded_image(image_path, size=None, radius_ratio=0.2, border_width=10):
    """
    Load an image, round its corners, and add a white border.
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGBA")
            
            # Resize if size is provided (optional, but good for consistency)
            if size:
                img = img.resize(size, Image.Resampling.LANCZOS)
            
            w, h = img.size
            
            # Create a mask for rounded corners
            mask = Image.new("L", (w, h), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, w, h), radius=min(w, h) * radius_ratio, fill=255)
            
            # Apply the mask to the image
            rounded_img = Image.new("RGBA", (w, h))
            rounded_img.paste(img, (0, 0), mask=mask)
            
            # Create a new image for the border
            if border_width > 0:
                new_w = w + 2 * border_width
                new_h = h + 2 * border_width
                final_img = Image.new("RGBA", (new_w, new_h), (255, 255, 255, 0))
                
                # Draw the white rounded border background
                draw_border = ImageDraw.Draw(final_img)
                draw_border.rounded_rectangle((0, 0, new_w, new_h), radius=min(new_w, new_h) * radius_ratio, fill="white")
                
                # Center the rounded image on top
                final_img.paste(rounded_img, (border_width, border_width), rounded_img)
                return final_img
            
            return rounded_img
    except Exception as e:
        logger.error(f"Error creating rounded image: {e}")
        return None


def generate_wifi_qr_code(ssid: str, password: str, save_path: str, center_image_path: str = None):

    """
    Generate a QR code for a table.
    
    Args:
        endpoint: The endpoint to encode in the QR code
        table_id: The ID of the table
        center_image_path: The path to the image to be used as the center of the QR code
        save_path: The path to save the QR code image
        ssid: The SSID (name) of the Wi-Fi network
        password: The password of the Wi-Fi network
    """

    try :
        qr = qrcode.QRCode(
            version= None, # The version parameter is an integer from 1 to 40 that controls the size of the QR Code (the smallest, version 1, is a 21x21 matrix). Set to None and use the fit parameter when making the code to determine this automatically.
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,

        )
        # Wi-Fi credentials in the format "WIFI:T:WPA;S:SSID;P:password;;"
        wifi_data = f"WIFI:T:WPA;S:{ssid};P:{password};;"

        qr.add_data(wifi_data)
        
        qr.make(fit=True)
        
        # Prepare embedded image if provided
        embedded_img = None
        if center_image_path:
            # Let's create the rounded image first.
            embedded_img = make_rounded_image(center_image_path, border_width=20) # Add a nice thick border

        img = qr.make_image(fill='black', 
                            back_color='white',
                            image_factory=StyledPilImage,
                            module_drawer=RoundedModuleDrawer(),
                            color_mask=RadialGradiantColorMask(),
                            embedded_image=embedded_img) # Use embedded_image object, not path


        os.makedirs(save_path, exist_ok=True)
        img.save(os.path.join(save_path, "wifi.png"))
        logger.info(
                "wifi.qrcode.created",
                language=LANG,
            )
    except Exception as e:
        logger.error(
                "wifi.qrcode.error",
                language=LANG,
                error=str(e)
            )
        return False
        
    return True

if __name__ == "__main__":

    # Testing
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "../assets/zeco_simple.png")
    save_dir = os.path.join(current_dir, "../assets/qrcodes")


    generate_wifi_qr_code(  ssid="SFR_5DEF_5GHz",     
                            password="6bmkkpj4kzf56izzc9ms", 
                            save_path=save_dir, 
                            center_image_path=image_path)

    generate_qr_code_for_tables(endpoint="http://JEDUAPF:80", 
                                tables=[9, 99, 999], 
                                save_path=save_dir)
