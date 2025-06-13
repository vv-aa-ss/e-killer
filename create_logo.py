from PIL import Image, ImageDraw, ImageFont
import os

# Создаем новое изображение с прозрачным фоном
width = 500
height = 500
image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)

# Рисуем круг
circle_bbox = [50, 50, width-50, height-50]
draw.ellipse(circle_bbox, fill=(0, 120, 212, 255))

# Добавляем текст
text = "EKiller"
# Используем стандартный шрифт, так как пользовательские шрифты могут быть недоступны
font_size = 100
try:
    font = ImageFont.truetype("arial.ttf", font_size)
except:
    font = ImageFont.load_default()

# Центрируем текст
text_bbox = draw.textbbox((0, 0), text, font=font)
text_width = text_bbox[2] - text_bbox[0]
text_height = text_bbox[3] - text_bbox[1]
text_x = (width - text_width) // 2
text_y = (height - text_height) // 2

# Рисуем текст
draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

# Сохраняем изображение
image.save("logo.png", "PNG")
print("Логотип создан: logo.png") 