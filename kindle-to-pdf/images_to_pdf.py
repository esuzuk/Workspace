"""
画像ファイルをPDFに結合するスクリプト
連番の画像ファイルを読み込み、1つのPDFファイルとして結合
"""
import os
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import glob


def images_to_pdf(input_dir: str, output_pdf: str, page_size: tuple = A4):
    """
    フォルダ内の連番画像をPDFに結合
    
    Args:
        input_dir: 画像が保存されているディレクトリ
        output_pdf: 出力PDFファイル名
        page_size: PDFのページサイズ（デフォルト: A4）
    """
    # 画像ファイルを取得（連番順にソート）
    image_files = sorted(glob.glob(os.path.join(input_dir, "*.png")) + 
                        glob.glob(os.path.join(input_dir, "*.jpg")) +
                        glob.glob(os.path.join(input_dir, "*.jpeg")))
    
    if not image_files:
        print(f"エラー: {input_dir} に画像ファイルが見つかりません。")
        return
    
    print(f"{len(image_files)}個の画像ファイルが見つかりました。")
    print("PDFに変換中...")
    
    # PDFを作成
    c = canvas.Canvas(output_pdf, pagesize=page_size)
    page_width, page_height = page_size
    
    for i, image_file in enumerate(image_files, 1):
        try:
            # 画像を開く
            img = Image.open(image_file)
            
            # 画像サイズを取得
            img_width, img_height = img.size
            
            # A4サイズに合わせてスケール（余白を残す）
            margin = 20  # 上下左右の余白（ポイント）
            available_width = page_width - (margin * 2)
            available_height = page_height - (margin * 2)
            
            # アスペクト比を保ちながらリサイズ
            scale_w = available_width / img_width
            scale_h = available_height / img_height
            scale = min(scale_w, scale_h)
            
            new_width = img_width * scale
            new_height = img_height * scale
            
            # 中央に配置するための位置を計算
            x = (page_width - new_width) / 2
            y = (page_height - new_height) / 2
            
            # 画像をリサイズ
            img_resized = img.resize((int(new_width), int(new_height)), Image.Resampling.LANCZOS)
            
            # PDFに画像を追加
            img_reader = ImageReader(img_resized)
            c.drawImage(img_reader, x, y, width=new_width, height=new_height)
            
            # 新しいページを追加（最後の画像以外）
            if i < len(image_files):
                c.showPage()
            
            print(f"処理中: {i}/{len(image_files)} - {os.path.basename(image_file)}")
            
        except Exception as e:
            print(f"エラー: {image_file} の処理中にエラーが発生しました: {e}")
            continue
    
    # PDFを保存
    c.save()
    print(f"\n完了！PDFファイルを保存しました: {output_pdf}")


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='画像ファイルをPDFに結合します'
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
        default='output.pdf',
        help='出力PDFファイル名（デフォルト: output.pdf）'
    )
    
    args = parser.parse_args()
    
    images_to_pdf(
        input_dir=args.input_dir,
        output_pdf=args.output
    )


if __name__ == "__main__":
    main()
