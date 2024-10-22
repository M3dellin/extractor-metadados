from PIL import Image, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
import os
import datetime
import json
import hashlib
import numpy as np
from pathlib import Path

class ImageMetadataExtractor:
    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}
    
    def get_file_metadata(self, filepath):
        """Extrai metadados básicos do arquivo"""
        file_stats = os.stat(filepath)
        return {
            'Nome do arquivo': os.path.basename(filepath),
            'Tamanho': f"{round(file_stats.st_size / (1024 * 1024), 2)} MB",
            'Data de criação': datetime.datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'Última modificação': datetime.datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'Extensão': os.path.splitext(filepath)[1].lower(),
            'Caminho completo': os.path.abspath(filepath),
            'Hash MD5': self._calculate_file_hash(filepath)
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
                colors = self._analyze_color_palette(img)
                color_info = [f"Cor {i+1}: {c['color']} ({c['percentage']}%)" 
                            for i, c in enumerate(colors)]
                
                return {
                    'Dimensões': f"{img.size[0]}x{img.size[1]} pixels",
                    'Proporção': f"{round(img.size[0] / img.size[1], 2)}:1",
                    'Modo de cor': img.mode,
                    'Formato': img.format,
                    'Animada': 'Sim' if getattr(img, 'is_animated', False) else 'Não',
                    'Frames': getattr(img, 'n_frames', 1),
                    'DPI': img.info.get('dpi', 'Não disponível'),
                    'Cores dominantes': '\n                '.join(color_info)
                }
        except Exception as e:
            return {'Erro': f'Erro ao processar imagem: {str(e)}'}
    
    def _analyze_color_palette(self, img, n_colors=5):
        """Analisa as cores dominantes na imagem"""
        try:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img.thumbnail((150, 150))
            np_img = np.array(img)
            pixels = np_img.reshape(-1, 3)
            
            unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
            
            top_colors = []
            for color, count in sorted(zip(unique_colors, counts), 
                                    key=lambda x: x[1], reverse=True)[:n_colors]:
                hex_color = '#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2])
                percentage = round((count / pixels.shape[0]) * 100, 2)
                top_colors.append({'color': hex_color, 'percentage': percentage})
            
            return top_colors
            
        except Exception as e:
            return [{'color': 'erro', 'percentage': 0}]
    
    def get_exif_metadata(self, filepath):
        """Extrai metadados EXIF da imagem"""
        try:
            with Image.open(filepath) as img:
                exif = {}
                
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    for tag_id, value in img._getexif().items():
                        tag = TAGS.get(tag_id, tag_id)
                        
                        if tag == 'GPSInfo':
                            gps_data = {}
                            for gps_tag_id in value:
                                gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                gps_data[gps_tag] = value[gps_tag_id]
                            exif['Dados GPS'] = self._process_gps_info(gps_data)
                        else:
                            if isinstance(value, bytes):
                                try:
                                    value = value.decode()
                                except:
                                    value = str(value)
                            exif[tag] = str(value)
                
                return exif if exif else {"Informação": "Sem dados EXIF disponíveis"}
                
        except Exception as e:
            return {'Erro': f'Erro ao extrair EXIF: {str(e)}'}
    
    def _process_gps_info(self, gps_data):
        """Processa informações GPS dos metadados EXIF"""
        try:
            if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                lat = self._convert_to_degrees(gps_data['GPSLatitude'])
                lon = self._convert_to_degrees(gps_data['GPSLongitude'])
                
                if gps_data.get('GPSLatitudeRef', 'N') != 'N':
                    lat = -lat
                if gps_data.get('GPSLongitudeRef', 'E') != 'E':
                    lon = -lon
                
                return {
                    'Latitude': f"{lat:.6f}°",
                    'Longitude': f"{lon:.6f}°",
                    'Altitude': f"{gps_data.get('GPSAltitude', 'N/A')} m",
                    'Horário GPS': str(gps_data.get('GPSTimeStamp', 'N/A'))
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

def main():
    print("\n=== Extrator de Metadados de Imagens ===\n")
    
    # Solicita o caminho da imagem
    while True:
        filepath = input("Digite o caminho completo da imagem (ou 'sair' para encerrar): ").strip()
        
        if filepath.lower() == 'sair':
            print("\nPrograma encerrado.")
            break
        
        if not os.path.exists(filepath):
            print("\nErro: Arquivo não encontrado. Tente novamente.\n")
            continue
        
        # Verifica extensão
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}:
            print("\nErro: Formato de arquivo não suportado.",
                  "Formatos suportados: JPG, PNG, TIFF, BMP, GIF\n")
            continue
        
        # Processa a imagem
        extractor = ImageMetadataExtractor()
        
        print("\nProcessando imagem...\n")
        
        # Coleta metadados
        file_meta = extractor.get_file_metadata(filepath)
        image_meta = extractor.get_image_metadata(filepath)
        exif_meta = extractor.get_exif_metadata(filepath)
        
        # Exibe resultados
        print("=== Metadados do Arquivo ===")
        for key, value in file_meta.items():
            print(f"{key}: {value}")
        
        print("\n=== Metadados da Imagem ===")
        for key, value in image_meta.items():
            print(f"{key}: {value}")
        
        print("\n=== Metadados EXIF ===")
        for key, value in exif_meta.items():
            if isinstance(value, dict):
                print(f"\n{key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"{key}: {value}")
        
        # Pergunta se quer salvar
        while True:
            save = input("\nDeseja salvar os metadados em um arquivo JSON? (s/n): ").lower()
            if save in ['s', 'n']:
                break
            print("Por favor, responda com 's' para sim ou 'n' para não.")
        
        if save == 's':
            output_path = os.path.splitext(filepath)[0] + "_metadados.json"
            metadata = {
                "Metadados do Arquivo": file_meta,
                "Metadados da Imagem": image_meta,
                "Metadados EXIF": exif_meta
            }
            
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=4, ensure_ascii=False)
                print(f"\nMetadados salvos em: {output_path}")
            except Exception as e:
                print(f"\nErro ao salvar arquivo: {e}")
        
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()