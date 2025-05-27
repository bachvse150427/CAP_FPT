import os
import glob
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
from datetime import datetime
from pydantic import BaseModel
import logging
import traceback

logs_dir = "logs"
os.makedirs(logs_dir, exist_ok=True)

log_timestamp = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
log_file = os.path.join(logs_dir, f"api_{log_timestamp}.log")

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Unified Stock Data API",
    description="API to get latest stock predictions data for both BB and UD models",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

class StockData(BaseModel):
    date: str
    symbol: str
    prediction: float

class StockQuery(BaseModel):
    ticker: str
    model: str
    month_year: str
    data_type: str

def get_latest_csv(data_type="BB"):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        if data_type.upper() not in ["BB", "UD"]:
            raise ValueError(f"Invalid data_type: {data_type}. Must be 'BB' or 'UD'")
            
        sub_dir = data_type.upper()
        data_dir = os.path.join(current_dir, "Get_Data", sub_dir)
        
        if not os.path.exists(data_dir):
            logger.error(f"Directory not found: {data_dir}")
            raise FileNotFoundError(f"Directory not found: {data_dir}")
        
        pattern = os.path.join(data_dir, "mongodb_data_*.csv")
        csv_files = glob.glob(pattern)
        
        logger.info(f"Found CSV files in {sub_dir}: {csv_files}")
        
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {sub_dir} directory")
        
        latest_file = max(csv_files, key=os.path.getctime)
        logger.info(f"Latest CSV file for {sub_dir}: {latest_file}")
        
        if not os.path.isfile(latest_file):
            raise FileNotFoundError(f"File not found: {latest_file}")
            
        df = pd.read_csv(latest_file)
        logger.info(f"File loaded successfully. Columns: {df.columns.tolist()}")
        
        return latest_file
    except Exception as e:
        logger.error(f"Error in get_latest_csv for {data_type}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.get("/available-filters")
def get_available_filters(data_type: str = Query("BB", description="Market State: BB or UD")):
    try:
        latest_file = get_latest_csv(data_type)
        df = pd.read_csv(latest_file)
        
        df['Date_Obj'] = pd.to_datetime(df['Date'])
        df['Full_Date'] = df['Date_Obj'].dt.strftime('%Y-%m-%d')
        
        return {
            "data_type": data_type,
            "tickers": sorted(df['Ticker'].unique().tolist()),
            "models": sorted(df['Model'].unique().tolist()),
            "dates": sorted(df['Full_Date'].unique().tolist())
        }
    except Exception as e:
        logger.error(f"Error in get_available_filters for {data_type}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stock-all-models")
def get_stock_all_models(
    ticker: str = Query(..., description="Stock ticker symbol (Required)"),
    market_state: str = Query(..., description="Market State: BB or UD (Required)"),
    date: str = Query(None, description="Date format (e.g., 2024-03-15). Optional - if not provided, returns all dates")
):
    try:
        if market_state.upper() not in ["BB", "UD"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid market_state: {market_state}. Must be either 'BB' or 'UD'"
            )
        
        if not ticker or ticker.isspace():
            raise HTTPException(
                status_code=400,
                detail="Ticker cannot be empty"
            )
        
        latest_file = get_latest_csv(market_state)
        logger.info(f"Reading file for ticker {ticker}, date {date}, market_state {market_state}")
        
        df = pd.read_csv(latest_file)
        logger.info(f"Data loaded. Columns: {df.columns.tolist()}")
        
        required_columns = ['Ticker', 'Date', 'Prediction', 'Model', 'F1_Score', 'Confidence']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if ticker not in df['Ticker'].unique():
            raise HTTPException(
                status_code=404,
                detail=f"Ticker '{ticker}' not found in {market_state} data"
            )
        
        df['Date_Obj'] = pd.to_datetime(df['Date'])
        df['Full_Date'] = df['Date_Obj'].dt.strftime('%Y-%m-%d')
        
        ticker_df = df[df['Ticker'] == ticker]
        
        if date:
            try:
                target_date = pd.to_datetime(date)
                
                filtered_df = ticker_df[ticker_df['Full_Date'] == date]
                
                if filtered_df.empty:
                    logger.info(f"No data found for {ticker} on {date}, searching for nearest previous date")
                    
                    previous_dates = ticker_df[ticker_df['Date_Obj'] < target_date]
                    
                    if not previous_dates.empty:
                        nearest_date_idx = previous_dates['Date_Obj'].idxmax()
                        nearest_date = previous_dates.loc[nearest_date_idx]
                        nearest_full_date = nearest_date['Full_Date']
                        
                        logger.info(f"Found nearest previous date: {nearest_full_date}")
                        filtered_df = ticker_df[ticker_df['Full_Date'] == nearest_full_date]
                        
                        if not filtered_df.empty:
                            logger.info(f"Using data from {nearest_full_date} instead of requested {date}")
                        else:
                            raise HTTPException(
                                status_code=404,
                                detail=f"No data found for Ticker={ticker}, Date={date} or any previous date"
                            )
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail=f"No data found for Ticker={ticker}, Date={date} or any previous date"
                        )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid date format: {date}. Use YYYY-MM-DD format."
                )
        else:
            filtered_df = ticker_df
        
        if filtered_df.empty:
            error_msg = f"No data found for Ticker={ticker}"
            if date:
                error_msg += f", Date={date}"
            error_msg += f", Market-State={market_state}"
            raise HTTPException(status_code=404, detail=error_msg)
        
        result_df = filtered_df[['Ticker', 'Model', 'Full_Date', 'Prediction', 'Confidence', 'F1_Score']]
        
        models = sorted(filtered_df['Model'].unique().tolist())
        
        model_statistics = {}
        for model in models:
            model_df = filtered_df[filtered_df['Model'] == model]
            total_pred = len(model_df)
            avg_f1_score = model_df['F1_Score'].mean() * 100
            
            model_statistics[model] = {
                "total_predictions": total_pred,
                "average_f1_score": float(avg_f1_score),
                "dates": sorted(model_df['Full_Date'].unique().tolist()),
                "total_dates": len(model_df['Full_Date'].unique())
            }
        
        total_predictions = len(result_df)
        avg_f1_score = result_df['F1_Score'].mean() * 100
        
        actual_dates = sorted(filtered_df['Full_Date'].unique())
        actual_date = actual_dates[0] if actual_dates else None
        
        return JSONResponse(
            content={
                "status": "success",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "market_state": market_state.upper(),
                "query_params": {
                    "ticker": ticker,
                    "requested_date": date if date else "all",
                    "actual_date": actual_date if date else "all"
                },
                "available_models": models,
                "total_models": len(models),
                "overall_statistics": {
                    "total_predictions": total_predictions,
                    "average_f1_score": float(avg_f1_score)
                },
                "model_statistics": model_statistics,
                "data": result_df.to_dict('records')
            }
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in get_stock_all_models for {market_state}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/latest-date-all-ticker-data")
def get_latest_date_all_ticker_data(
    market_state: str = Query(..., description="Market State: BB or UD (Required)")
):
    try:
        if market_state.upper() not in ["BB", "UD"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid market_state: {market_state}. Must be either 'BB' or 'UD'"
            )
        
        latest_file = get_latest_csv(market_state)
        logger.info(f"Reading file for market_state {market_state}")
        
        df = pd.read_csv(latest_file)
        logger.info(f"Data loaded. Columns: {df.columns.tolist()}")
        
        required_columns = ['Ticker', 'Date', 'Prediction', 'Model', 'F1_Score', 'Confidence']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        df = df.replace({pd.NA: None, pd.NaT: None, float('nan'): None})
        
        df['Date_Obj'] = pd.to_datetime(df['Date'])
        df['Full_Date'] = df['Date_Obj'].dt.strftime('%Y-%m-%d')

        latest_data = []
        tickers = df['Ticker'].unique()
        
        for ticker in tickers:
            ticker_df = df[df['Ticker'] == ticker]
            latest_date = ticker_df['Date_Obj'].max()
            
            if pd.isna(latest_date):
                logger.warning(f"No valid date found for ticker {ticker}")
                continue
                
            latest_ticker_data = ticker_df[ticker_df['Date_Obj'] == latest_date]
            
            if latest_ticker_data.empty:
                logger.warning(f"No data found for ticker {ticker} at date {latest_date}")
                continue
                
            latest_data.append({
                'ticker': ticker,
                'latest_date': latest_date.strftime('%Y-%m-%d'),
                'models': []
            })
            
            for model in latest_ticker_data['Model'].unique():
                model_data = latest_ticker_data[latest_ticker_data['Model'] == model]
                
                if model_data.empty:
                    continue
                    
                prediction = model_data['Prediction'].iloc[0]
                confidence = model_data['Confidence'].iloc[0]
                f1_score = model_data['F1_Score'].iloc[0]
                
                latest_data[-1]['models'].append({
                    'model_name': model,
                    'prediction': int(prediction) if prediction is not None else None,
                    'confidence': float(confidence) if confidence is not None else None,
                    'f1_score': float(f1_score) if f1_score is not None else None
                })
                
        latest_data.sort(key=lambda x: x['ticker'])
        
        return JSONResponse(
            content={
                "status": "success",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "market_state": market_state.upper(),
                "total_tickers": len(latest_data),
                "data": latest_data
            }
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in get_latest_ticker_data for {market_state}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

def print_csv_files():
    logger.info("="*50)
    logger.info("CHECKING CSV FILES IN USE:")
    logger.info("="*50)
    
    try:
        bb_file = get_latest_csv("BB")
        logger.info(f"✅ BB FILE: {os.path.basename(bb_file)}")
        logger.info(f"   Full path: {bb_file}")
        
        bb_modified_time = datetime.fromtimestamp(os.path.getmtime(bb_file))
        logger.info(f"   Last updated: {bb_modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        bb_size = os.path.getsize(bb_file) / 1024
        logger.info(f"   Size: {bb_size:.2f} KB")
    except Exception as e:
        logger.error(f"❌ Error reading BB file: {str(e)}")
    
    logger.info("-"*50)
    
    try:
        ud_file = get_latest_csv("UD")
        logger.info(f"✅ UD FILE: {os.path.basename(ud_file)}")
        logger.info(f"   Full path: {ud_file}")
        
        ud_modified_time = datetime.fromtimestamp(os.path.getmtime(ud_file))
        logger.info(f"   Last updated: {ud_modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        ud_size = os.path.getsize(ud_file) / 1024
        logger.info(f"   Size: {ud_size:.2f} KB")
    except Exception as e:
        logger.error(f"❌ Error reading UD file: {str(e)}")
    
    logger.info("="*50)
    
if __name__ == "__main__":
    import uvicorn

    print_csv_files()

    logger.info("Starting Unified API server...")
    uvicorn.run("API:app", host="0.0.0.0", port=8080, log_level="info")
