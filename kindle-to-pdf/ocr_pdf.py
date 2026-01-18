"""
OCR機能を使用してPDFにテキストレイヤーを追加するスクリプト
ローカルOCR（Tesseract）またはAI（OpenAI GPT-4o / Google Gemini 1.5 Pro）を使用
"""
import os
import base64
from PIL import Image
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import glob


def encode_image(image_path: str) -> str:
    """画像をbase64エンコード"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def ocr_with_tesseract(image_path: str) -> str:
    """
    Tesseract OCRを使用してOCRを実行（ローカル、APIキー不要）
    
    Args:
        image_path: 画像ファイルのパス
    
    Returns:
        抽出されたテキスト
    """
    try:
        import pytesseract
        from PIL import Image
        
        # 画像を読み込む
        img = Image.open(image_path)
        
        # OCRを実行（日本語と英語をサポート）
        # 日本語を使用する場合は 'jpn' を追加: lang='jpn+eng'
        text = pytesseract.image_to_string(img, lang='jpn+eng')
        
        return text
        
    except ImportError:
        print("エラー: pytesseractライブラリがインストールされていません。")
        print("インストール: pip install pytesseract")
        print("また、Tesseract本体のインストールも必要です:")
        print("  macOS: brew install tesseract tesseract-lang")
        print("  Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-jpn")
        return ""
    except Exception as e:
        print(f"エラー: Tesseract OCR処理中にエラーが発生しました: {e}")
        print("Tesseractが正しくインストールされているか確認してください。")
        return ""


def ocr_with_openai(image_path: str, api_key: str) -> str:
    """
    OpenAI GPT-4oを使用してOCRを実行
    
    Args:
        image_path: 画像ファイルのパス
        api_key: OpenAI APIキー
    
    Returns:
        抽出されたテキスト
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        # 画像をbase64エンコード
        base64_image = encode_image(image_path)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "この画像に含まれるすべてのテキストを正確に書き起こしてください。改行や段落構造も可能な限り保持してください。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4000
        )
        
        return response.choices[0].message.content
        
    except ImportError:
        print("エラー: openaiライブラリがインストールされていません。")
        print("インストール: pip install openai")
        return ""
    except Exception as e:
        print(f"エラー: OCR処理中にエラーが発生しました: {e}")
        return ""


def ocr_with_gemini(image_path: str, api_key: str) -> str:
    """
    Google Gemini 1.5 Proを使用してOCRを実行
    
    Args:
        image_path: 画像ファイルのパス
        api_key: Google APIキー
    
    Returns:
        抽出されたテキスト
    """
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # 画像を読み込む
        img = Image.open(image_path)
        
        response = model.generate_content([
            "この画像に含まれるすべてのテキストを正確に書き起こしてください。改行や段落構造も可能な限り保持してください。",
            img
        ])
        
        return response.text
        
    except ImportError:
        print("エラー: google-generativeaiライブラリがインストールされていません。")
        print("インストール: pip install google-generativeai")
        return ""
    except Exception as e:
        print(f"エラー: OCR処理中にエラーが発生しました: {e}")
        return ""


def create_searchable_pdf(image_dir: str, output_pdf: str, api_key: str = None, 
                          provider: str = "tesseract", page_size: tuple = A4):
    """
    画像からOCRでテキストを抽出し、検索可能なPDFを作成
    
    Args:
        image_dir: 画像が保存されているディレクトリ
        output_pdf: 出力PDFファイル名
        api_key: APIキー（OpenAIまたはGoogle、ローカルOCRの場合は不要）
        provider: 使用するOCRプロバイダー（"tesseract", "openai", "gemini"）
        page_size: PDFのページサイズ（デフォルト: A4）
    """
    # 画像ファイルを取得（連番順にソート）
    image_files = sorted(glob.glob(os.path.join(image_dir, "*.png")) + 
                        glob.glob(os.path.join(image_dir, "*.jpg")) +
                        glob.glob(os.path.join(image_dir, "*.jpeg")))
    
    if not image_files:
        print(f"エラー: {image_dir} に画像ファイルが見つかりません。")
        return
    
    print(f"{len(image_files)}個の画像ファイルが見つかりました。")
    print(f"OCRプロバイダー: {provider}")
    
    # OCR関数を選択
    if provider.lower() == "tesseract":
        ocr_func = lambda img_path, key=None: ocr_with_tesseract(img_path)
        print("ローカルOCR（Tesseract）を使用します（APIキー不要）")
    elif provider.lower() == "gemini":
        if not api_key:
            print("エラー: Geminiを使用するにはAPIキーが必要です。")
            return
        ocr_func = ocr_with_gemini
        print("Google Gemini 1.5 Proを使用します")
    elif provider.lower() == "openai":
        if not api_key:
            print("エラー: OpenAIを使用するにはAPIキーが必要です。")
            return
        ocr_func = ocr_with_openai
        print("OpenAI GPT-4oを使用します")
    else:
        print(f"エラー: 不明なプロバイダー: {provider}")
        print("利用可能なプロバイダー: tesseract, openai, gemini")
        return
    
    print("OCR処理を開始します（時間がかかる場合があります）...\n")
    
    # PDFを作成
    c = canvas.Canvas(output_pdf, pagesize=page_size)
    page_width, page_height = page_size
    
    for i, image_file in enumerate(image_files, 1):
        try:
            # 画像を開く
            img = Image.open(image_file)
            
            # 画像サイズを取得
            img_width, img_height = img.size
            
            # A4サイズに合わせてスケール
            margin = 20
            available_width = page_width - (margin * 2)
            available_height = page_height - (margin * 2)
            
            scale_w = available_width / img_width
            scale_h = available_height / img_height
            scale = min(scale_w, scale_h)
            
            new_width = img_width * scale
            new_height = img_height * scale
            
            # 中央に配置
            x = (page_width - new_width) / 2
            y = (page_height - new_height) / 2
            
            # 画像をリサイズ
            img_resized = img.resize((int(new_width), int(new_height)), Image.Resampling.LANCZOS)
            
            # PDFに画像を追加
            from reportlab.lib.utils import ImageReader
            img_reader = ImageReader(img_resized)
            c.drawImage(img_reader, x, y, width=new_width, height=new_height)
            
            # OCRでテキストを抽出
            print(f"OCR処理中: {i}/{len(image_files)} - {os.path.basename(image_file)}")
            if provider.lower() == "tesseract":
                text = ocr_func(image_file)
            else:
                text = ocr_func(image_file, api_key)
            
            if text:
                # 透明テキストレイヤーとして追加
                # 注: reportlabでは完全に透明なテキストは難しいため、
                # 非常に小さなフォントサイズで白色テキストとして配置
                text_obj = c.beginText()
                text_obj.setTextRenderMode(3)  # 非表示モード（検索可能だが表示されない）
                text_obj.setFont("Helvetica", 1)  # 1ポイントのフォント
                text_obj.setTextColor(1, 1, 1, alpha=0)  # 完全に透明
                
                # テキストを画像の位置に配置
                # 簡易実装：テキストを画像の範囲内に配置
                lines = text.split('\n')
                line_height = new_height / max(len(lines), 1)
                
                for j, line in enumerate(lines[:int(new_height/line_height)]):
                    if line.strip():
                        text_obj.setTextOrigin(x, y + new_height - (j * line_height))
                        text_obj.textLine(line[:100])  # 長い行は切り詰め
                
                c.drawText(text_obj)
            
            # 新しいページを追加（最後の画像以外）
            if i < len(image_files):
                c.showPage()
            
        except Exception as e:
            print(f"エラー: {image_file} の処理中にエラーが発生しました: {e}")
            continue
    
    # PDFを保存
    c.save()
    print(f"\n完了！検索可能なPDFファイルを保存しました: {output_pdf}")
    print("注意: 完全に透明なテキストレイヤーの実装はPDFビューアによって異なる場合があります。")


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='OCRを使用して画像からテキストを抽出し、検索可能なPDFを作成します'
    )
    parser.add_argument(
        '--input-dir',
        type=str,
        default='screenshots',
        help='画像が保存されているディレクトリ（デフォルト: screenshots）'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='output_searchable.pdf',
        help='出力PDFファイル名（デフォルト: output_searchable.pdf）'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='APIキー（OpenAIまたはGoogle、ローカルOCRの場合は不要）。環境変数OPENAI_API_KEYまたはGOOGLE_API_KEYからも読み取れます'
    )
    parser.add_argument(
        '--provider',
        type=str,
        choices=['tesseract', 'openai', 'gemini'],
        default='tesseract',
        help='使用するOCRプロバイダー（デフォルト: tesseract、APIキー不要）'
    )
    
    args = parser.parse_args()
    
    # 環境変数からAPIキーを取得（指定されていない場合）
    api_key = args.api_key
    if not api_key and args.provider in ['openai', 'gemini']:
        if args.provider == 'openai':
            api_key = os.environ.get('OPENAI_API_KEY')
        elif args.provider == 'gemini':
            api_key = os.environ.get('GOOGLE_API_KEY')
        
        if not api_key:
            print(f"エラー: {args.provider}を使用するにはAPIキーが必要です。")
            print("以下のいずれかの方法でAPIキーを指定してください:")
            print(f"  1. --api-keyオプションで指定")
            print(f"  2. 環境変数{'OPENAI_API_KEY' if args.provider == 'openai' else 'GOOGLE_API_KEY'}を設定")
            print(f"  3. --provider tesseract でローカルOCRを使用（APIキー不要）")
            return
    
    create_searchable_pdf(
        image_dir=args.input_dir,
        output_pdf=args.output,
        api_key=api_key,
        provider=args.provider
    )


if __name__ == "__main__":
    main()
