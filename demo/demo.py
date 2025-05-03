import sys
sys.path.append("./src")
import polarsUtils as plu
import pandas as pd
from typing import List, Dict
import polars as pl
from prophet import Prophet
import matplotlib.pyplot as plt
import os

#Columns at datasource 
WAREHOUSE = "Almacen"
DATE = "Fecha"
CUSTOMER = "Cliente"
SELLER = "Vendedor"
PRODUCT_CONCAT = "ProdConcat"
QUANTITY = "Cantidad"
SALE_PRICE = "PrecioVenta"
PAYMENT_METHODS = "Metodos De Pago"
NO_MOV = "NoMov"

#Constants for analysis
DIRECTORY = "./data/dummy" # Directory where the excel files are located
KEYWORDS = "dummy" # Keyword to search for in the file names
SALES_COLUMNS =  [
    WAREHOUSE,
    DATE,
    SALE_PRICE
]
OUTPUT_PATH = "./output/demo/prophet" # Path to save the output file
OUTPUT_FILE_NAME = "dataCleaned" # Name of the output file

#Columns for analysis Prophet
DS_COLUMN = "ds"
Y_COLUMN = "y"


from typing import Dict

def cleanAndTransformDataFrameByWarehouse(dfList: List[pl.DataFrame]) -> Dict[str, pl.DataFrame]:
    """
    Transforms a list of Polars DataFrames grouped by warehouse into a dictionary.
    Each DataFrame keeps only DATE and SALE_PRICE, and renames them to 'ds' and 'y'.

    :param dfList: List of Polars DataFrames (each filtered by WAREHOUSE)
    :return: Dictionary with warehouse name as key and cleaned DataFrame as value
    """
    warehouseDict = {}

    for df in dfList:
        # Get unique warehouse value (should be the same for all rows)
        warehouseName = df.select(WAREHOUSE).unique().item()
        
        # Select and rename columns
        dfClean = df.select([DATE, SALE_PRICE]).rename({
            DATE: DS_COLUMN,
            SALE_PRICE: Y_COLUMN
        })

        # Group by date and sum sales
        dfClean = dfClean.group_by(DS_COLUMN).agg([
            pl.col(Y_COLUMN).sum().alias(Y_COLUMN)
        ])

        #plu.saveDataFrameToExcel(dfClean, OUTPUT_PATH, "dataCleaned"+warehouseName+".xlsx")

        warehouseDict[warehouseName] = dfClean

    return warehouseDict



def forecastByWarehouse(dfDict: Dict[str, pl.DataFrame], periods: int = 30, outputDir: str = "./output/bi/forecasts") -> Dict[str, pd.DataFrame]:
    """
    Applies Prophet to each warehouse DataFrame, generates forecasts, and saves plots.

    :param dfDict: Dictionary with warehouse names as keys and cleaned Polars DataFrames as values
    :param periods: Number of days to forecast
    :param outputDir: Directory to save forecast plots
    :return: Dictionary with forecasts (key = warehouse name, value = forecast DataFrame)
    """
    os.makedirs(outputDir, exist_ok=True)
    forecastResults = {}

    for warehouse, df in dfDict.items():
        # Convert to pandas
        dfPandas = df.to_pandas()

        # Train Prophet
        model = Prophet()
        model.add_seasonality(name='Monthly', period=30.5, fourier_order=5)
        model.fit(dfPandas)

        # Forecast
        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)

        forecastResults[warehouse] = forecast

        # Guardar componentes por separado (tendencia, estacionalidad)
        fig_plot = model.plot(forecast)
        filename_fig_plot = f"{outputDir}/plot_{warehouse.replace(' ', '_').lower()}.png"
        fig_plot.savefig(filename_fig_plot)
        plt.close(fig_plot)


        # Guardar componentes por separado (tendencia, estacionalidad)
        fig_components = model.plot_components(forecast)
        filename_components = f"{outputDir}/components_{warehouse.replace(' ', '_').lower()}.png"
        fig_components.savefig(filename_components)
        plt.close(fig_components)




        

    return forecastResults



def main():
    dfSales = plu.createMergedDataFrameFromExcelMatch(directory= DIRECTORY, keyword= KEYWORDS, columns= SALES_COLUMNS, saveToExcel= False, outputPath= OUTPUT_PATH, outputFileName= OUTPUT_FILE_NAME)

    dfSales = plu.formatDateColumn(dfSales, DATE, outputFormat="%Y-%m-%d")

    #dfSales = plu.filterLastNDaysFromMaxDate(dfSales, 360, DATE)

    dfSalesByWarehouse = plu.splitDataFrameByColumn(dfSales, WAREHOUSE)

    dfCleaned = cleanAndTransformDataFrameByWarehouse(dfSalesByWarehouse)

    forecastByWarehouse(dfCleaned, periods=30, outputDir=OUTPUT_PATH)


main()