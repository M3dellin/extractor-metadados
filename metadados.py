from PIL import Image, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
import os
import datetime
import json
import hashlib
from collections import defaultdict
import numpy as np
from pathlib import Path
import warnings

class ImageMetadataExtractor:
    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}
    
    def get_file_metadata(self, filepath):
        """Extrai metadados básicos do arquivo"""
        file_stats = os.stat(filepath)
        return {
            'filename': os.path.basename(filepath),
            'file_size_bytes': file_stats.st_size,
            'file_size_mb': round(file_stats.st_size / (1024 * 1024), 2),
            'creation_time': datetime.datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'modification_time': datetime.datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'file_extension': os.path.splitext(filepath)[1].lower(),
            'file_path': os.path.abspath(filepath),
            'file_hash_md5': self._calculate_file_hash(filepath)
        }
    
    def _calculate_file_hash(self, filepath):
        """Calcula o hash MD5 do arquivo"""
        md5_hash = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def get_image_metadata(self, filepath):
        """Extrai metadados técnicos da imagem"""
        try:
            with Image.open(filepath) as img:
                return {
                    'dimensions': img.size,
                    'width': img.size[0],
                    'height': img.size[1],
                    'aspect_ratio': round(img.size[0] / img.size[1], 2),
                    'color_mode': img.mode,
                    'format': img.format,
                    'is_animated': getattr(img, 'is_animated', False),
                    'n_frames': getattr(img, 'n_frames', 1),
                    'color_palette': self._analyze_color_palette(img),
                    'dpi': img.info.get('dpi', None)
                }
        except Exception as e:
            return {'error': f'Erro ao processar imagem: {str(e)}'}
    
    def _analyze_color_palette(self, img, n_colors=5):
        """Analisa as cores dominantes na imagem"""
        try:
            # Converte para RGB se necessário
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Redimensiona para análise mais rápida
            img.thumbnail((150, 150))
            
            # Converte imagem para array numpy
            np_img = np.array(img)
            pixels = np_img.reshape(-1, 3)
            
            # Agrupa cores similares
            unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
            
            # Pega as cores mais frequentes
            top_colors = []
            for color, count in sorted(zip(unique_colors, counts), key=lambda x: x[1], reverse=True)[:n_colors]:
                hex_color = '#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2])
                percentage = round((count / pixels.shape[0]) * 100, 2)
                top_colors.append({'color': hex_color, 'percentage': percentage})
            
            return top_colors
            
        except Exception as e:
            return {'error': f'Erro na análise de cores: {str(e)}'}
    
    def get_exif_metadata(self, filepath):
        """Extrai metadados EXIF da imagem"""
        try:
            with Image.open(filepath) as img:
                exif = {}
                
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    for tag_id, value in img._getexif().items():
                        tag = TAGS.get(tag_id, tag_id)
                        
                        # Processa dados GPS separadamente
                        if tag == 'GPSInfo':
                            gps_data = {}
                            for gps_tag_id in value:
                                gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                gps_data[gps_tag] = value[gps_tag_id]
                            exif['GPS'] = self._process_gps_info(gps_data)
                        else:
                            # Converte bytes para string quando necessário
                            if isinstance(value, bytes):
                                try:
                                    value = value.decode()
                                except:
                                    value = str(value)
                            exif[tag] = str(value)
                
                return exif
                
        except Exception as e:
            return {'error': f'Erro ao extrair EXIF: {str(e)}'}
    
    def _process_gps_info(self, gps_data):
        """Processa informações GPS dos metadados EXIF"""
        try:
            if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                lat = self._convert_to_degrees(gps_data['GPSLatitude'])
                lon = self._convert_to_degrees(gps_data['GPSLongitude'])
                
                # Ajusta direção
                if gps_data.get('GPSLatitudeRef', 'N') != 'N':
                    lat = -lat
                if gps_data.get('GPSLongitudeRef', 'E') != 'E':
                    lon = -lon
                
                return {
                    'latitude': lat,
                    'longitude': lon,
                    'altitude': gps_data.get('GPSAltitude', None),
                    'timestamp': gps_data.get('GPSTimeStamp', None)
                }
            return None
        except:
            return None
    
    def _convert_to_degrees(self, value):
        """Converte coordenadas GPS para graus decimais"""
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    
    def analyze_image(self, filepath):
        """Analisa uma imagem e retorna todos os metadados disponíveis"""
        if not os.path.exists(filepath):
            return {'error': 'Arquivo não encontrado'}
            
        file_extension = os.path.splitext(filepath)[1].lower()
        if file_extension not in self.supported_formats:
            return {'error': 'Formato de arquivo não suportado'}
            
        return {
            'file_metadata': self.get_file_metadata(filepath),
            'image_metadata': self.get_image_metadata(filepath),
            'exif_metadata': self.get_exif_metadata(filepath)
        }
    
    def save_metadata(self, metadata, output_path):
        """Salva os metadados em um arquivo JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)

# Exemplo de uso
if __name__ == "__main__":
    extractor = ImageMetadataExtractor()
    
    # Exemplo de análise de uma imagem
    image_path = "caminho/para/sua/imagem.jpg"
    metadata = extractor.analyze_image(image_path)
    
    # Salvar resultados
    extractor.save_metadata(metadata, "metadados_imagem.json")
    
    # Imprimir resultados
    print("\nMetadados extraídos:")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))