"""
Google Spreadsheetとの連携を管理するモジュール
"""
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpreadsheetManager:
    """Google Spreadsheet管理クラス"""
    
    def __init__(self, spreadsheet_id: str, credentials_path: str = "credentials.json"):
        """
        初期化
        
        Args:
            spreadsheet_id: Google SpreadsheetのID
            credentials_path: サービスアカウントのJSONキーファイルパス
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = credentials_path
        self.client = None
        self.spreadsheet = None
        self._connect()
    
    def _connect(self):
        """Google Spreadsheetに接続"""
        try:
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(f"認証情報ファイルが見つかりません: {self.credentials_path}")
            
            creds = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=scope
            )
            
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            logger.info("Google Spreadsheetに接続しました")
        except Exception as e:
            logger.error(f"Google Spreadsheet接続エラー: {str(e)}")
            raise
    
    def _get_or_create_sheet(self, sheet_name: str, headers: list[str]) -> gspread.Worksheet:
        """
        シートを取得または作成
        
        Args:
            sheet_name: シート名
            headers: ヘッダー行
        
        Returns:
            Worksheet: シートオブジェクト
        """
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            # ヘッダーを確認
            existing_headers = sheet.row_values(1)
            if not existing_headers or existing_headers != headers:
                sheet.clear()
                sheet.append_row(headers)
            return sheet
        except gspread.exceptions.WorksheetNotFound:
            # シートが存在しない場合は作成
            sheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            sheet.append_row(headers)
            logger.info(f"シートを作成しました: {sheet_name}")
            return sheet
    
    def save_portfolio(self, portfolio_data: list[dict]):
        """
        保有株式データを保存
        
        Args:
            portfolio_data: 保有株式データのリスト
        """
        try:
            headers = [
                'Ticker', 'Shares', 'Purchase Price per Share', 'Purchase Date',
                'Current Price', 'Current Value', 'Profit/Loss', 'Profit/Loss Rate (%)',
                'Last Updated'
            ]
            
            sheet = self._get_or_create_sheet('Portfolio', headers)
            
            # 既存データをクリア（ヘッダーを除く）
            if len(sheet.get_all_values()) > 1:
                sheet.delete_rows(2, len(sheet.get_all_values()))
            
            # データを書き込み
            for item in portfolio_data:
                row = [
                    item.get('ticker', ''),
                    item.get('shares', 0),
                    item.get('purchase_price_per_share', 0),
                    item.get('purchase_date', ''),
                    item.get('current_price', 0),
                    item.get('current_value', 0),
                    item.get('profit_loss', 0),
                    item.get('profit_loss_rate', 0),
                    item.get('last_updated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                ]
                sheet.append_row(row)
            
            logger.info(f"保有株式データを保存しました: {len(portfolio_data)}件")
        except Exception as e:
            logger.error(f"保有株式データ保存エラー: {str(e)}")
            raise
    
    def load_portfolio(self) -> list[dict]:
        """
        保有株式データを読み込み
        
        Returns:
            list[dict]: 保有株式データのリスト
        """
        try:
            sheet = self.spreadsheet.worksheet('Portfolio')
            records = sheet.get_all_records()
            
            portfolio = []
            for record in records:
                portfolio.append({
                    'ticker': record.get('Ticker', ''),
                    'shares': float(record.get('Shares', 0)),
                    'purchase_price_per_share': float(record.get('Purchase Price per Share', 0)),
                    'purchase_date': record.get('Purchase Date', ''),
                    'current_price': float(record.get('Current Price', 0)),
                    'current_value': float(record.get('Current Value', 0)),
                    'profit_loss': float(record.get('Profit/Loss', 0)),
                    'profit_loss_rate': float(record.get('Profit/Loss Rate (%)', 0)),
                    'last_updated': record.get('Last Updated', '')
                })
            
            logger.info(f"保有株式データを読み込みました: {len(portfolio)}件")
            return portfolio
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("Portfolioシートが存在しません")
            return []
        except Exception as e:
            logger.error(f"保有株式データ読み込みエラー: {str(e)}")
            raise
    
    def save_recommendation(self, recommendation: dict):
        """
        売買推奨を保存
        
        Args:
            recommendation: 推奨データ
        """
        try:
            headers = [
                'Date', 'Ticker', 'Type', 'Current Price', 'Recommended Price',
                'Reason', 'RSI', 'MACD', 'MA_20', 'MA_50', 'MA_200',
                'Logic', 'Confidence', 'Data Source'
            ]
            
            sheet = self._get_or_create_sheet('Recommendations', headers)
            
            data_source = recommendation.get('data_source', {})
            row = [
                recommendation.get('recommendation_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                recommendation.get('ticker', ''),
                recommendation.get('recommendation_type', ''),
                recommendation.get('current_price', 0),
                recommendation.get('recommended_price', 0),
                recommendation.get('reason', ''),
                data_source.get('rsi', ''),
                data_source.get('macd', ''),
                data_source.get('ma_20', ''),
                data_source.get('ma_50', ''),
                data_source.get('ma_200', ''),
                recommendation.get('logic', ''),
                recommendation.get('confidence', 0),
                str(data_source)
            ]
            
            sheet.append_row(row)
            logger.info(f"推奨を保存しました: {recommendation.get('ticker')} - {recommendation.get('recommendation_type')}")
        except Exception as e:
            logger.error(f"推奨保存エラー: {str(e)}")
            raise
    
    def save_data_log(self, log_data: dict):
        """
        データ取得ログを保存
        
        Args:
            log_data: ログデータ
        """
        try:
            headers = ['Date', 'Ticker', 'Status', 'Data Retrieved', 'Error Message']
            
            sheet = self._get_or_create_sheet('Data Logs', headers)
            
            row = [
                log_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                log_data.get('ticker', ''),
                log_data.get('status', ''),
                log_data.get('data_retrieved', ''),
                log_data.get('error_message', '')
            ]
            
            sheet.append_row(row)
        except Exception as e:
            logger.error(f"ログ保存エラー: {str(e)}")
            # ログ保存のエラーは致命的ではないので、警告のみ
            logger.warning(f"ログを保存できませんでした: {str(e)}")
