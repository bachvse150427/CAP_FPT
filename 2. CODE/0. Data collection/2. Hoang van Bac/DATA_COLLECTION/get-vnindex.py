import os
import pandas as pd
from vnstock3 import Vnstock
from datetime import datetime
import time
import random
import logging
import sys

# Thiết lập logging chi tiết
log_filename = f'0-Data/logs/data/{datetime.now().strftime("%Y%m%d_%H%M%S")}_vnindex_download.log'
log_dir = os.path.dirname(log_filename)
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def fetch_vnindex_data(max_retries=3):
    """
    Lấy dữ liệu VNINDEX từ vnstock3 với cơ chế retry.
    Giả sử VNINDEX có ticker là "VNINDEX" và nguồn được sử dụng là "TCBS".
    """
    ticker = "VNINDEX"
    source = "TCBS"
    current_year = datetime.now().year
    all_data = []
    
    # Lấy dữ liệu theo từng năm từ 2006 đến năm hiện tại
    for year in range(2005, current_year + 1):
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        logging.info(f"Đang lấy dữ liệu VNINDEX năm {year} từ nguồn {source}...")
        
        for attempt in range(max_retries):
            try:
                delay = random.uniform(2, 5)
                logging.info(f"Lần thử {attempt+1}/{max_retries} - Delay {delay:.1f}s")
                time.sleep(delay)
                
                stock = Vnstock().stock(symbol=ticker, source=source)
                data = stock.quote.history(start=start_date, end=end_date)
                
                if data is not None and not data.empty:
                    logging.info(f"Lấy được {len(data)} bản ghi cho năm {year}")
                    all_data.append(data)
                else:
                    logging.info(f"Không có dữ liệu cho năm {year}")
                break  # thoát vòng lặp retry nếu thành công
            except Exception as e:
                logging.error(f"Lỗi lấy dữ liệu năm {year} (lần thử {attempt+1}): {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    logging.info(f"Chờ {wait_time}s rồi thử lại...")
                    time.sleep(wait_time)
                else:
                    logging.warning(f"Bỏ qua năm {year} sau {max_retries} lần thử.")
    
    if all_data:
        combined_data = pd.concat(all_data, ignore_index=True)
        # Chuẩn hóa tên cột nếu cần (ví dụ: đổi 'time' thành 'Date', 'close' thành 'Close',...)
        column_mappings = {
            'time': 'Date',
            'tradingDate': 'Date',
            'open': 'Open',
            'openPrice': 'Open',
            'high': 'High',
            'highPrice': 'High',
            'low': 'Low',
            'lowPrice': 'Low',
            'close': 'Close',
            'closePrice': 'Close',
            'volume': 'Volume',
            'tradingVolume': 'Volume'
        }
        rename_cols = {old: new for old, new in column_mappings.items() if old in combined_data.columns}
        combined_data = combined_data.rename(columns=rename_cols)
        
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        if all(col in combined_data.columns for col in required_cols):
            result = combined_data[required_cols].copy()
            result['Ticker'] = ticker
            result['Date'] = pd.to_datetime(result['Date'])
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                result[col] = pd.to_numeric(result[col], errors='coerce')
            result = result.sort_values('Date').drop_duplicates()
            logging.info(f"Tổng số bản ghi VNINDEX: {len(result)}")
            return result
        else:
            logging.warning("Dữ liệu không có đủ các cột cần thiết.")
    else:
        logging.error("Không lấy được dữ liệu VNINDEX từ bất kỳ năm nào.")
    
    return None

def save_vnindex_data():
    output_dir = '0-Data/data/Tickers'
    os.makedirs(output_dir, exist_ok=True)
    
    data = fetch_vnindex_data()
    if data is not None:
        file_path = os.path.join(output_dir, "VNINDEX.csv")
        data.to_csv(file_path, index=False)
        logging.info(f"Đã lưu dữ liệu VNINDEX vào: {file_path}")
    else:
        logging.error("Không lấy được dữ liệu VNINDEX sau tất cả các lần thử.")

if __name__ == "__main__":
    save_vnindex_data()
