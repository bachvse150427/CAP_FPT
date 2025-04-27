import os
import pandas as pd
from vnstock3 import Vnstock
from datetime import datetime
import time
import random
import logging
import sys
from tqdm import tqdm

# Thiết lập logging chi tiết
log_filename = f'0-Data/logs/data/{datetime.now().strftime("%Y%m%d_%H%M%S")}_stock_download.log'

# Create the directory if it doesn't exist
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

def fetch_stock_data(ticker, max_retries=3):
    """
    Lấy dữ liệu cho một mã cổ phiếu với cơ chế retry và delay
    """
    sources = ['TCBS', 'VNDIRECT']
    
    for source in sources:
        logging.info(f"\n{'='*50}")
        logging.info(f"Đang xử lý mã {ticker} từ nguồn {source}")
        
        for attempt in range(max_retries):
            try:
                delay = random.uniform(2, 5)
                logging.info(f"Lần thử {attempt + 1}/{max_retries} - Delay {delay:.1f}s")
                time.sleep(delay)
                
                stock = Vnstock().stock(symbol=ticker, source=source)
                current_year = datetime.now().year
                all_data = []
                
                # Lấy dữ liệu theo từng năm
                for year in range(2006, current_year + 1):
                    try:
                        start_date = f"{year}-01-01"
                        end_date = f"{year}-12-31"
                        
                        logging.info(f"Đang lấy dữ liệu năm {year}...")
                        time.sleep(1)
                        
                        data = stock.quote.history(
                            start=start_date,
                            end=end_date
                        )
                        
                        if data is not None and not data.empty:
                            logging.info(f"Lấy được {len(data)} bản ghi cho năm {year}")
                            all_data.append(data)
                        else:
                            logging.info(f"Không có dữ liệu cho năm {year}")
                            
                    except Exception as e:
                        if "Too Many Requests" in str(e):
                            wait_time = 10
                            logging.warning(f"Quá nhiều request, chờ {wait_time}s")
                            time.sleep(wait_time)
                        else:
                            logging.error(f"Lỗi lấy dữ liệu năm {year}: {str(e)}")
                        continue
                
                if all_data:
                    combined_data = pd.concat(all_data, ignore_index=True)
                    logging.info(f"Tổng số bản ghi: {len(combined_data)}")
                    
                    # Chuẩn hóa tên cột
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
                    
                    rename_cols = {old: new for old, new in column_mappings.items() 
                                 if old in combined_data.columns}
                    combined_data = combined_data.rename(columns=rename_cols)
                    
                    required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                    if all(col in combined_data.columns for col in required_cols):
                        result = combined_data[required_cols].copy()
                        result['Ticker'] = ticker
                        
                        # Chuyển đổi kiểu dữ liệu
                        result['Date'] = pd.to_datetime(result['Date'])
                        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                        result[numeric_cols] = result[numeric_cols].apply(pd.to_numeric, errors='coerce')
                        
                        # Kiểm tra dữ liệu null
                        null_counts = result[numeric_cols].isnull().sum()
                        if null_counts.any():
                            logging.warning(f"Có giá trị null trong dữ liệu: {null_counts.to_dict()}")
                        
                        # Sắp xếp và loại bỏ trùng lặp
                        result = result.sort_values('Date').drop_duplicates()
                        
                        if not result.empty:
                            logging.info(f"Xử lý thành công {ticker} từ {source}")
                            logging.info(f"Khoảng thời gian: {result['Date'].min()} đến {result['Date'].max()}")
                            logging.info(f"Số ngày giao dịch: {result['Date'].nunique()}")
                            return ticker, result, None
                
                logging.warning(f"Không có dữ liệu hợp lệ cho {ticker} từ {source}")
                
            except Exception as e:
                error_msg = str(e)
                if "Too Many Requests" in error_msg and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    logging.warning(f"Too Many Requests cho {ticker}, thử lại sau {wait_time}s")
                    time.sleep(wait_time)
                    continue
                logging.error(f"Lỗi khi lấy dữ liệu {ticker} từ {source}: {error_msg}")
                break
    
    return ticker, None, "Không lấy được dữ liệu từ tất cả các nguồn"

def get_stock_data():
    """
    Lấy dữ liệu cho tất cả các mã chứng khoán
    """
    output_dir = '0-Data/data/Tickers'
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        logging.info("\nBắt đầu quá trình tải dữ liệu")
        logging.info("="*50)
        
        # Lấy danh sách mã chứng khoán
        logging.info("Đang lấy danh sách mã chứng khoán...")
        stock = Vnstock().stock(symbol='VN30F1M', source='TCBS')
        listing = stock.listing.all_symbols()
        
        # Lọc mã HOSE
        if 'exchange' in listing.columns:
            symbols = listing[listing['exchange'] == 'HOSE']['ticker'].tolist()
            logging.info(f"Tìm thấy {len(symbols)} mã HOSE")
        else:
            symbols = listing['ticker'].tolist()
            logging.info(f"Không tìm thấy thông tin sàn, lấy tất cả {len(symbols)} mã")
        
        successful = []
        failed = []
        
        # Xử lý từng mã một với progress bar
        for ticker in tqdm(symbols, desc="Đang tải dữ liệu"):
            try:
                ticker, data, error = fetch_stock_data(ticker)
                
                if data is not None:
                    file_path = os.path.join(output_dir, f"{ticker}.csv")
                    data.to_csv(file_path, index=False)
                    successful.append(ticker)
                    
                    start_date = data['Date'].min().strftime('%Y-%m-%d')
                    end_date = data['Date'].max().strftime('%Y-%m-%d')
                    logging.info(f"Đã lưu dữ liệu {ticker} ({start_date} đến {end_date})")
                else:
                    failed.append((ticker, error))
                    logging.error(f"Thất bại: {ticker} - {error}")
                    
            except Exception as e:
                failed.append((ticker, str(e)))
                logging.error(f"Lỗi xử lý {ticker}: {str(e)}")
            
            time.sleep(2)
        
        # Tổng kết chi tiết
        logging.info("\n" + "="*50)
        logging.info("KẾT QUẢ TẢI DỮ LIỆU:")
        logging.info(f"Tổng số mã: {len(symbols)}")
        logging.info(f"Thành công: {len(successful)} ({len(successful)/len(symbols)*100:.1f}%)")
        logging.info(f"Thất bại: {len(failed)} ({len(failed)/len(symbols)*100:.1f}%)")
        
        if failed:
            logging.info("\nDanh sách mã thất bại:")
            for ticker, error in failed:
                logging.info(f"- {ticker}: {error}")
        
        logging.info("\nHoàn thành quá trình tải dữ liệu!")
        logging.info("="*50)
        
        return len(successful), failed
        
    except Exception as e:
        logging.error(f"Lỗi khởi tạo: {str(e)}")
        return 0, []

if __name__ == "__main__":
    try:
        successful_count, failed_downloads = get_stock_data()
    except Exception as e:
        logging.error(f"Lỗi chương trình: {str(e)}")