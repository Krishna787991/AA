import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Tuple
import uuid

import pandas as pd
import re
import json
import warnings

warnings.filterwarnings(
    "ignore",
    message="Converting to PeriodArray/Index representation will drop timezone information.*"
)

AA_NAMESPACE = "http://homecredit.net/rcm/cbp/accountaggregator"

NS = {
    "acc": AA_NAMESPACE
}


CHANNELS = {
    "UPI": ["UPI", "UPIAR", "UPIAB"],
    "IMPS": ["IMPS"],
    "NEFT": ["NEFT"],
    "RTGS": ["RTGS"],
    "NACH": ["NACH"],
    "CARD": ["CARD"],
    "ATM": ["ATM"],
    "AEPS": ["AEPS"],
    "CHEQUE": ["CHEQUE"],
    "CASH": ["CASH"],
    "AUTO_DEBIT": ["AUTO_DEBIT"],
}


CATEGORY_KEYWORDS = {
    "salary": ["SALARY", "PAYROLL"],
    "interest": ["INT.PD", "INTEREST"],
    "cash": ["ATM", "AEPS","CWDR"],
    "investment": ["ZERODHA", "UPSTOX", "GROWW", "MUTUAL FUND"],
    "loan": ["LOAN"],
    "emi": ["EMI", "ECS"],
    "credit_card": ["CARD PAYMENT", "CREDIT CARD"],
    "penalty": ["RTN CHG","NACH RTN CHG","ACH RTN","NACH RET",
                "AMB CHG","AMB PENALTY","AQB CHG","MAB CHG",
                "CHQ RTN","INW RET","ECS RTN","ECS REJECT",
                "SI RETURN","SI FAIL","PENAL CHRG","PENAL INT",
                "GST ON CHRG","RETURN"]
}




class AccountAggregatorParser:

    def __init__(self, xml_path: str):
        self.xml_path = Path(xml_path)

        if not self.xml_path.exists():
            raise FileNotFoundError(
                f"XML file not found: {xml_path}"
            )

        tree = ET.parse(self.xml_path)
        self.root = tree.getroot()

        self.account = (
            self.root
            .find(".//acc:item", NS)
        )

        if self.account is None:
            raise ValueError(
                "Account node not found in XML."
            )

    @staticmethod
    def get_text(node, tag: str):
        if node is None:
            return None

        element = node.find(f"acc:{tag}", NS)
        return (
            element.text.strip()
            if element is not None and element.text
            else None
        )

    def extract_summary(self) -> pd.DataFrame:

        summary = self.account.find(
            "acc:Summary",
            NS
        )

        data = {
            "ifsc": self.get_text(summary, "ifscCode"),
            "branch": self.get_text(summary, "branch"),
            "status": self.get_text(summary, "status"),
            "currency": self.get_text(summary, "currency"),
            "micr_code": self.get_text(summary, "micrCode"),
            "account_type": self.get_text(summary, "type"),
            "opening_date": self.get_text(summary, "openingDate"),
            "drawing_limit": self.get_text(summary, "drawingLimit"),
            "current_balance": self.get_text(summary, "currentBalance"),
            "current_od_limit": self.get_text(summary, "currentODLimit"),
            "balance_datetime": self.get_text(summary, "balanceDateTime"),
        }

        return pd.DataFrame([data])

    def extract_profile(self) -> pd.DataFrame:

        holder = self.account.find(
            ".//acc:Holder/acc:item",
            NS
        )

        profile = {
            "name": self.get_text(holder, "name"),
            "dob": self.get_text(holder, "dob"),
            "pan": self.get_text(holder, "pan"),
            "email": self.get_text(holder, "email"),
            "mobile": self.get_text(holder, "mobile"),
            "address": self.get_text(holder, "address"),
            "nominee": self.get_text(holder, "nominee"),
            "ckyc_registered": self.get_text(holder, "ckycCompliance")
        }

        return pd.DataFrame([profile])
    
    def extract_all_other_info(self) -> pd.DataFrame:

        holder = self.account.find(
            ".//acc:Holder/acc:item",
            NS
        )

        summary = self.account.find(
            "acc:Summary",
            NS
        )

        transactions = self.account.find(
            ".//acc:Transactions",
            NS
        )

        data = {
            "end_date": self.get_text(
                transactions,
                "endDate"
            ),
            "account_number": self.get_text(
                self.account,
                "maskedAccountNumber"
            ),
            "mobile": self.get_text(holder, "mobile"),
            "full_address": self.get_text(holder, "address"),
            "latest_balance": self.get_text(
                summary,
                "currentBalance"
            ),
            "ifsc_code": self.get_text(summary, "ifscCode"),
            "full_name": self.get_text(holder, "name"),
            "dob": self.get_text(holder, "dob"),
            "bank_name": self.get_text(
                self.account,
                "bank"
            ),
            "link_reference_no": self.get_text(
                self.account,
                "linkReferenceNumber"
            ),
            "email": self.get_text(holder, "email"),
            "start_date": self.get_text(
                transactions,
                "startDate"
            )
        }

        return pd.DataFrame([data])
    
    def extract_transactions(self) -> pd.DataFrame:

        transactions = self.account.findall(
            ".//acc:Transaction/acc:item",
            NS
        )

        rows = []

        for txn in transactions:

            rows.append({
                "txn_id": self.get_text(txn, "txnId"),
                "mode": self.get_text(txn, "mode"),
                "type": self.get_text(txn, "type"),
                "amount": self.get_text(txn, "amount"),
                "narration": self.get_text(txn, "narration"),
                "reference": self.get_text(txn, "reference"),
                "value_date": self.get_text(txn, "valueDate"),
                "transaction_timestamp":
                    self.get_text(txn, "transactionTimestamp"),
                "transactional_balance":
                    self.get_text(txn, "currentBalance"),
            })

        df = pd.DataFrame(rows)

        self._transform_transaction_data(df)

        return df

    @staticmethod
    def _transform_transaction_data(df: pd.DataFrame):

        df["amount"] = pd.to_numeric(
            df["amount"],
            errors="coerce"
        )

        df["transactional_balance"] = pd.to_numeric(
            df["transactional_balance"],
            errors="coerce"
        )

        df["value_date"] = pd.to_datetime(
            df["value_date"],
            errors="coerce"
        )

        df["transaction_timestamp"] = pd.to_datetime(
            df["transaction_timestamp"],
            utc=True,
            errors="coerce"
        )
        
        df["is_credit"] = (
            df["type"].eq("CREDIT")
        )

        df["is_debit"] = (
            df["type"].eq("DEBIT")
        )




class TransactionClassifier:

    def __init__(self):
        pass

    def normalize_text(self, text):

        if pd.isna(text):
            return ""

        text = str(text)
        text = text.upper()
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text
    

    def identify_channel(self,mode, narration):

        mode = str(mode).upper()
        narration = str(narration).upper()
        
        for channel, keywords in CHANNELS.items():
            if channel == mode:
                return channel

            if any(word in narration for word in keywords):
                return channel

        return "OTHER"


    def extract_counterparty(self, narration):
        narration = narration.upper()
        tokens = narration.split("/")
        ignore = {"UPI","UPIAB","UPIAR","CR","DR","IMPS","RTGS","NEFT","P2A","P2M","REV","TRANSFER"}

        for token in tokens:
            token = token.strip()
            if len(token) < 3:
                continue

            if token in ignore:
                continue
            if token.isdigit():
                continue
            return token
        
        return None

    
    def contains_keyword(self, narration, keywords):
        narration = narration.upper()

        for word in keywords:
            if re.search(rf"\b{re.escape(word)}\b", narration):
                return True

        return False


    def classify(self, df):
        df = df.copy()
        df["narration_clean"] = df["narration"].apply(self.normalize_text)
    
        df["payment_channel"] = (
            df.apply(
                lambda row:
                self.identify_channel(
                    row["mode"],
                    row["narration_clean"]
                ),
                axis=1
            )
        )

        df["counterparty"] = (
            df["narration_clean"]
            .apply(self.extract_counterparty)
        )

        for category, keywords in CATEGORY_KEYWORDS.items():
            df[f"is_{category}"] = (
                df["narration_clean"]
                .apply(
                    lambda x:
                    self.contains_keyword(
                        x,
                        keywords
                    )
                )
            )
        return df

    

class BalanceAnalytics:

    @staticmethod
    def create_daily_balance_series(df: pd.DataFrame,end_date=None) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=[
                    "value_date",
                    "transaction_timestamp",
                    "transactional_balance",
                    "narration_clean",
                    "type",
                    "year_month"
                ]
            )

        df = df.copy()

        # Ensure datatypes
        df["value_date"] = pd.to_datetime(df["value_date"], utc=True)
        df["transaction_timestamp"] = pd.to_datetime(
            df["transaction_timestamp"],
            utc=True    
        )


        df = (df.sort_values(
                ["value_date", "transaction_timestamp"],
                ascending=[True, True]
            )
            .reset_index(drop=True)
        )

        start_date = df["value_date"].min()

        if end_date is None:
            end_date = df["value_date"].max()
        else:
            end_date = pd.to_datetime(end_date, utc=True)

        # Create missing dates
        full_dates = pd.date_range(start=start_date,end=end_date,freq="D",tz="UTC")

        dates_df = pd.DataFrame({
            "value_date": full_dates
        })

        # Keep all transactions and inject missing days
        merged_df = pd.merge(
            dates_df,
            df[["value_date","transaction_timestamp","transactional_balance","narration_clean","type"]],
            on="value_date",
            how="outer"
        )

        # Sort again after merge
        merged_df = (
            merged_df.sort_values(
                ["value_date", "transaction_timestamp"],
                ascending=[True, True],
                na_position="first"
            )
            .reset_index(drop=True)
        )

        # Carry forward balance for generated dates
        merged_df["transactional_balance"] =merged_df["transactional_balance"].ffill()
    

        merged_df["year_month"] =merged_df["value_date"].dt.to_period("M")

        # Restrict to requested end date
        merged_df = merged_df[merged_df["value_date"] <= end_date]

        return merged_df

    

    @staticmethod
    def monthly_metrics(daily_df: pd.DataFrame) -> pd.DataFrame:
        data_end_date = daily_df["value_date"].max()

        def last_7_day_features(month_df):

            month_df = month_df.sort_values(
                ["value_date", "transaction_timestamp"]
            )

            # Daily closing balances
            daily_close = (
                month_df
                .groupby("value_date")["transactional_balance"]
                .last()
            )
            
            last_7_dates = daily_close.tail(7).index

            # Average from closing balances
            last_7d_avg = daily_close.tail(7).mean()

            # All transactions from those 7 dates
            last_7_txns = month_df[
                month_df["value_date"].isin(last_7_dates)
            ]

            # Max balance date within the month
            max_balance_date = month_df.loc[
                    month_df["transactional_balance"].idxmax(),
                    "value_date"
                ]

            days_since_max_balance = (
                    data_end_date - max_balance_date
                ).days
            

            eod_balance_count_less_than_1000 = (
                daily_close < 1000
            ).sum()

            # daily_close.to_csv("daily_close.csv",index=False)
            
            return pd.Series({
                "days_since_max_balance":days_since_max_balance,
                "eod_balance_count_less_than_1000":eod_balance_count_less_than_1000,
                "median_eod_balance": daily_close.median(),
                "last_7d_avg": last_7d_avg,
                "last_7d_max": last_7_txns["transactional_balance"].max(),
                "last_7d_min": last_7_txns["transactional_balance"].min()
            })



        base_metrics = (
            daily_df
            .groupby("year_month")
            .agg(
                avg_balance=("transactional_balance", "mean"),
                max_balance=("transactional_balance", "max"),
                min_balance=("transactional_balance", "min"),
                month_end_balance=("transactional_balance", "last")
            )
        )

        
        last7_metrics = (
            daily_df
            .groupby("year_month")
            .apply(last_7_day_features, include_groups=False)
        )
        

        result = (
            base_metrics
            .join(last7_metrics)
            .reset_index()
        )

        result["days_since_max_balance"] = (
            result["days_since_max_balance"]
            .fillna(0)
            .astype(int)
        )

        return result


class TransactionFeatureGenerator:

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        df=df.copy()
        df["year_month"] = df["transaction_timestamp"].dt.to_period("M")


        grouped = df.groupby("year_month")

        features = pd.DataFrame()
        
        features["credit_count"] = grouped.apply(
            lambda x: (x["type"] == "CREDIT").sum()
        )

        features["debit_count"] = grouped.apply(
            lambda x: (x["type"] == "DEBIT").sum()
        )

        features["credit_amount"] = grouped.apply(
            lambda x: x.loc[x["type"] == "CREDIT", "amount"].sum()
        )

        features["debit_amount"] = grouped.apply(
            lambda x: x.loc[x["type"] == "DEBIT", "amount"].sum()
        )

        features["maximum_credit_amount"] = grouped.apply(
            lambda x: x.loc[x["type"] == "CREDIT", "amount"].max()
        ).fillna(0)

        features["maximum_debit_amount"] = grouped.apply(
            lambda x: x.loc[x["type"] == "DEBIT", "amount"].max()
        ).fillna(0)

        features["upi_credit_count"] = grouped.apply(
            lambda x: (
                (x["payment_channel"] == "UPI")
                & (x["type"] == "CREDIT")
            ).sum()
        )

        features["upi_debit_count"] = grouped.apply(
            lambda x: (
                (x["payment_channel"] == "UPI")
                & (x["type"] == "DEBIT")
            ).sum()
        )

        features["upi_credit_amount"] = grouped.apply(
            lambda x: x.loc[
                (x["payment_channel"] == "UPI")
                & (x["type"] == "CREDIT"),
                "amount"
            ].sum()
        )
  
        features["upi_debit_amount"] = grouped.apply(
            lambda x: x.loc[
                (x["payment_channel"] == "UPI")
                & (x["type"] == "DEBIT"),
                "amount"
            ].sum()
        )


        features["cash_withdrawal_amount"] = grouped.apply(
            lambda x: x.loc[
                (x["is_cash"]) &
                (x["amount"] % 1 == 0) & 
                (x["type"]=="DEBIT"),
                "amount"
            ].sum()
        )

        features["cash_withdrawal_count"] = grouped.apply(
            lambda x: (
                x["is_cash"] & (x["amount"] % 1 == 0) & (x["type"]=="DEBIT")
            ).sum()
        )

        features["third_party_credit_amount"] = grouped.apply(
            lambda x: x.loc[
                (x["type"] == "CREDIT")
                & x["counterparty"].notna(),
                "amount"
            ].sum()
        )

        features["max_credit_amount"] = grouped.apply(
            lambda x: x.loc[
                x["type"] == "CREDIT",
                "amount"
            ].max()
        ).fillna(0)

        features["max_debit_amount"] = grouped.apply(
            lambda x: x.loc[
                x["type"] == "DEBIT",
                "amount"
            ].max()
        ).fillna(0)

        features["penalty_count"] = grouped.apply(
            lambda x: (
                x["is_penalty"] &
                (x["type"].str.upper() == "DEBIT")
            ).sum()
        )

        features["penalty_amount"] = grouped.apply(
            lambda x: x.loc[
                x["is_penalty"] &
                (x["type"].str.upper() == "DEBIT"),
                "amount"
            ].sum()
        )

        return features.reset_index()
    
    
    
def to_bank_statement_json(df: pd.DataFrame) -> dict:
    return {
        "keys": {
            "bank_statement": [
                df.iloc[0].to_dict()
            ]
        }
    }


def create_feature_payload(
    feature_name,
    values,
    grouping="monthly",
    sortby="decreasing"
):
    return {
        "item": {
            "data": {
                feature_name: list(values)
            },
            "id": str(uuid.uuid4()),
            "config": {
                "period": len(values),
                "sortby": sortby,
                "grouping": grouping
            }
        }
    }



def compute(data):
    try:
        xml_message = data["message"] if isinstance(data, dict) else data
        parser = AccountAggregatorParser(data)

        df_customer = parser.extract_all_other_info()
    
        transactions_df = parser.extract_transactions()
    
        classifier = TransactionClassifier()
        classified_df = classifier.classify(transactions_df)

        feature_generator = TransactionFeatureGenerator()
        transactional_features_df = feature_generator.generate(classified_df)


        daily_df = BalanceAnalytics.create_daily_balance_series(
            classified_df,
            end_date="2026-08-24"
        )

        monthly_metrics_df = BalanceAnalytics.monthly_metrics(
            daily_df
        )

        json_data = to_bank_statement_json(df_customer)


        payload = {
            "data": {
                "insights": {},
                "keys": {}
            }
        }

        # Bank statement
        payload["data"]["keys"]["bank_statement"] = json_data["keys"]["bank_statement"]

        # All transactional features
        for col in transactional_features_df.columns:

            if col == "year_month":
                continue

            payload["data"]["keys"][f"grouped_{col}"] = (
                create_feature_payload(
                    col,
                    transactional_features_df[col]
                )
            )

        return {
            "status": True,
            "result": json.dumps(payload),
            "message": "OK",
            "version": "v3",
        }
    
    except Exception as e:
        return {
            "status": True,
            "result": f"{str(e)}",
            "message": "OK",
            "version": "v3",
        }

if __name__=="__main__":
    xml_path="data/AA_35090447.xml"
    
    response=compute(xml_path)
    print(response)
