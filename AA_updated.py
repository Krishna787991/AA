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
ONEMONEY_NAMESPACE = "http://homecredit.net/rcm/cbp/onemoney"   # only used to read onemoney.xml for validation

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
    # CHANGED: "ECS" removed. "ECS Txn Chrgs Incl GST" is a bank charge, NOT an EMI.
    # The real EMI in this data looks like  ACH-DR-CTHEROFINC-...  (handled in TransactionClassifier.classify)
    "emi": ["EMI"],
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

    # NEW: statement period, read from the XML instead of hard-coding "2026-08-24".
    # The daily balance series runs from start_date to end_date (both inclusive).
    def extract_statement_period(self) -> Tuple[pd.Timestamp, pd.Timestamp]:

        transactions = self.account.find(
            ".//acc:Transactions",
            NS
        )

        start_date = pd.Timestamp(self.get_text(transactions, "startDate"))
        end_date = pd.Timestamp(self.get_text(transactions, "endDate"))

        return start_date, end_date
    
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
        tokens = re.split(r'[/-]+', narration)

        ignore = {"UPI","UPIAB","UPIAR","CR","DR","IMPS","RTGS","NEFT","P2A","P2M","REV","TRANSFER"}

        for token in tokens:
            token = token.strip()
            if len(token) < 3:
                continue
            
            if re.fullmatch(r'[A-Z0-9]{15,}', token):
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

        # NEW: EMI = ACH / NACH debit where the payee is a NAME (a lender), e.g.
        #   ACH-DR-CTHEROFINC-70783434-...    -> EMI   (4365 every month in the reference)
        # but NOT when the payee is a number, e.g.
        #   ACH-DR-450300726901-0000KBM9...   -> NOT an EMI in the reference
        df["is_emi"] = (
            df["is_emi"]
            | df["narration_clean"].str.match(r"^N?ACH-DR-[A-Z]")
        )

        return df

    


class BalanceAnalytics:
    """
    ---------------------------------------------------------------------------
    HOW THE REFERENCE (onemoney.xml) CALCULATES THE BALANCE FEATURES
    ---------------------------------------------------------------------------
    1. Day / month of a transaction  = UTC date of transaction_timestamp
                                       (NOT value_date).

    2. Build a DAILY balance series for every calendar day from statement
       start_date to end_date:
         - day WITH transactions     -> balance after the LAST txn of the day (end-of-day)
         - day WITHOUT transactions  -> a "filler" day. Its value is the balance
                                        after the FIRST txn of the last active day.
                                        (carried forward, also across month boundaries)

    3. Every monthly feature is then a simple calculation on:
         txn rows   = the balance after each transaction of that month
         daily rows = one EOD value per calendar day of that month
         fillers    = the daily rows that are gap days

         avg_balance       = mean( txn rows + filler rows )       <- row average, not day average
         max / min_balance = max / min of txn rows (intra-day balances)
         month_end_balance = last value of the daily series
         median_eod_balance= median of the daily series
         eod_balance_count_less_than_1000 = number of days with daily value < 1000
         days_since_max_balance = end_date - date of the max txn balance
         last_7d_*         = same idea but only for the LAST 7 CALENDAR DAYS OF THE MONTH
                             (e.g. 25-31 for a 31 day month). If the statement has no data
                             in that window (current partial month) the value is 0.
    ---------------------------------------------------------------------------
    """

    @staticmethod
    def _txn_day(df: pd.DataFrame) -> pd.Series:
        # Calendar day of every transaction = UTC date of the transaction timestamp
        return (
            df["transaction_timestamp"]
            .dt.tz_convert("UTC")
            .dt.tz_localize(None)
            .dt.normalize()
        )

    @staticmethod
    def create_daily_balance_series(
        df: pd.DataFrame,
        start_date,
        end_date
    ) -> pd.DataFrame:
        """
        Returns one row per calendar day (start_date .. end_date):
            day | eod_balance | is_filler | year_month
        """

        df = df.copy()

        # Step 1: oldest -> newest (stable sort keeps the XML order for equal timestamps)
        df = df.sort_values("transaction_timestamp", kind="stable")
        df["day"] = BalanceAnalytics._txn_day(df)

        # Step 2: for each day that has transactions, remember
        #   - the LAST balance  (used as that day's end-of-day balance)
        #   - the FIRST balance (used later to fill the following empty days)
        last_of_day = df.groupby("day")["transactional_balance"].last()
        first_of_day = df.groupby("day")["transactional_balance"].first()

        # Fallback only: if the very first calendar day has no txn we need an opening balance.
        # opening = balance of first txn +/- its amount. (Not triggered in the sample data.)
        # first_txn = df.iloc[0]
        # if first_txn["type"] == "DEBIT":
        #     carry = first_txn["transactional_balance"] + first_txn["amount"]
        # else:
        #     carry = first_txn["transactional_balance"] - first_txn["amount"]

        # Step 3: walk through every calendar day
        records = []

        for day in pd.date_range(start=start_date, end=end_date, freq="D"):

            if day in last_of_day.index:
                # normal day -> end-of-day balance = last txn of the day
                records.append((day, last_of_day[day], False))

                # the value that empty days after this day will copy is the FIRST txn balance
                carry = first_of_day[day]

            else:
                # gap day -> filler row
                records.append((day, carry, True))

        daily_df = pd.DataFrame(
            records,
            columns=["day", "eod_balance", "is_filler"]
        )

        daily_df["year_month"] = daily_df["day"].dt.to_period("M")

        return daily_df

    

    @staticmethod
    def monthly_metrics(
        df: pd.DataFrame,
        daily_df: pd.DataFrame,
        end_date
    ) -> pd.DataFrame:
        """
        One row per month, newest month first (same order as onemoney.xml, M0 = latest month).
        """

        end_date = pd.Timestamp(end_date)

        df = df.copy()
        df["day"] = BalanceAnalytics._txn_day(df)
        df["year_month"] = df["day"].dt.to_period("M")

        results = []

        for year_month, daily_m in daily_df.groupby("year_month"):

            txn_m = df[df["year_month"] == year_month]

            # ---- building blocks for this month -----------------------------
            txn_balances = txn_m["transactional_balance"]                       # every txn row
            fillers = daily_m.loc[daily_m["is_filler"], "eod_balance"]          # gap-day rows
            eod = daily_m["eod_balance"]                                        # one value per day

            # ---- average balance: mean of (txn rows + filler rows) -----------
            all_rows = pd.concat([txn_balances, fillers])
            avg_balance = all_rows.mean() if len(all_rows) else 0

            # ---- max / min: intra-day txn balances ---------------------------
            max_balance = txn_balances.max() if len(txn_balances) else 0
            min_balance = txn_balances.min() if len(txn_balances) else 0

            # ---- month end balance: last day of the daily series -------------
            month_end_balance = eod.iloc[-1]

            # ---- median / count on the daily series --------------------------
            median_eod_balance = eod.median()
            eod_balance_count_less_than_1000 = int((eod < 1000).sum())

            # ---- days since max balance --------------------------------------
            if len(txn_m):
                max_balance_day = txn_m.loc[
                    txn_m["transactional_balance"].idxmax(), "day"
                ]
                days_since_max_balance = (end_date - max_balance_day).days
            else:
                days_since_max_balance = 0

            # ---- last 7 CALENDAR days of the month ---------------------------
            # window starts at (days_in_month - 7) days after the 1st: 31 day month -> day 25
            window_start = (
                year_month.start_time.normalize()
                + pd.Timedelta(days=year_month.days_in_month - 7)
            )

            daily_7 = daily_m[daily_m["day"] >= window_start]

            # rows used for max/min = txn rows of the window + filler rows of the window
            rows_7 = pd.concat([
                txn_m.loc[txn_m["day"] >= window_start, "transactional_balance"],
                daily_7.loc[daily_7["is_filler"], "eod_balance"],
            ])

            # avg uses the DAILY values of the window (7 days), 0 if the window has no data
            last_7d_avg = daily_7["eod_balance"].mean() if len(daily_7) else 0
            last_7d_max = rows_7.max() if len(rows_7) else 0
            last_7d_min = rows_7.min() if len(rows_7) else 0

            results.append({
                "year_month": year_month,
                "avg_balance": round(avg_balance, 2),
                "max_balance": max_balance,
                "min_balance": min_balance,
                "month_end_balance": month_end_balance,
                "days_since_max_balance": days_since_max_balance,
                "eod_balance_count_less_than_1000": eod_balance_count_less_than_1000,
                "median_eod_balance": round(median_eod_balance, 2),
                "last_7d_avg": round(last_7d_avg, 2),
                "last_7d_max": last_7d_max,
                "last_7d_min": last_7d_min,
            })

        return (
            pd.DataFrame(results)
            .sort_values("year_month", ascending=False)      # newest month first, like onemoney.xml
            .reset_index(drop=True)
        )


class TransactionFeatureGenerator:

   
    def generate(self, df: pd.DataFrame, start_date=None, end_date=None) -> pd.DataFrame:
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

        # (removed the duplicate max_credit_amount / max_debit_amount columns that repeated these two)
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

        # ------------------------------------------------------------------
        # NEW features (present in onemoney.xml, missing in the old code)
        # ------------------------------------------------------------------
        features["emi_debit_amount"] = grouped.apply(
            lambda x: x.loc[
                x["is_emi"] & (x["type"] == "DEBIT"),
                "amount"
            ].sum()
        )

        features["emi_debit_count"] = grouped.apply(
            lambda x: (
                x["is_emi"] & (x["type"] == "DEBIT")
            ).sum()
        )

        features["loan_credit_amount"] = grouped.apply(
            lambda x: x.loc[
                x["is_loan"] & (x["type"] == "CREDIT"),
                "amount"
            ].sum()
        )

        features["loan_credit_count"] = grouped.apply(
            lambda x: (
                x["is_loan"] & (x["type"] == "CREDIT")
            ).sum()
        )

        features["credit_card_payment_amount"] = grouped.apply(
            lambda x: x.loc[
                x["is_credit_card"] & (x["type"] == "DEBIT"),
                "amount"
            ].sum()
        )

        features["credit_card_payment_count"] = grouped.apply(
            lambda x: (
                x["is_credit_card"] & (x["type"] == "DEBIT")
            ).sum()
        )

        features["investment_credit_amount"] = grouped.apply(
            lambda x: x.loc[
                x["is_investment"] & (x["type"] == "CREDIT"),
                "amount"
            ].sum()
        )

        features["investment_debit_amount"] = grouped.apply(
            lambda x: x.loc[
                x["is_investment"] & (x["type"] == "DEBIT"),
                "amount"
            ].sum()
        )

     
        if start_date is not None and end_date is not None:
            all_months = pd.period_range(start_date, end_date, freq="M")
            features = features.reindex(all_months, fill_value=0)
            features.index.name = "year_month"

        # newest month first, like onemoney.xml (M0 = latest month)
        return features.reset_index().sort_values(
            "year_month", ascending=False
        ).reset_index(drop=True)
    
    
    
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


def build_feature_tables(xml_path):
    """
    Runs the whole pipeline and returns the three tables.
    (Pulled out of compute() so the same code can be used by compute() and by the validation below.)
    """
    parser = AccountAggregatorParser(xml_path)

    df_customer = parser.extract_all_other_info()
    start_date, end_date = parser.extract_statement_period()

    transactions_df = parser.extract_transactions()

    classifier = TransactionClassifier()
    classified_df = classifier.classify(transactions_df)

    # transaction level monthly features (counts, amounts, UPI, cash, EMI, salary ...)
    feature_generator = TransactionFeatureGenerator()
    transactional_features_df = feature_generator.generate(
        classified_df, start_date, end_date
    )

    # balance based monthly features (avg balance, last 7 days, median EOD ...)
    daily_df = BalanceAnalytics.create_daily_balance_series(
        classified_df,
        start_date=start_date,
        end_date=end_date          # CHANGED: taken from the XML, no longer hard-coded
    )

    monthly_metrics_df = BalanceAnalytics.monthly_metrics(
        classified_df,
        daily_df,
        end_date=end_date
    )

    return df_customer, transactional_features_df, monthly_metrics_df


def compute(data):
    try:
        # CHANGED: the old code built xml_message but then passed the whole `data` to the parser
        xml_path = data["message"] if isinstance(data, dict) else data
       
        df_customer, transactional_features_df, monthly_metrics_df = build_feature_tables(xml_path)
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

        # NEW: balance based monthly features (they were calculated before but never added to the payload)
        for col in monthly_metrics_df.columns:

            if col == "year_month":
                continue

            payload["data"]["keys"][f"grouped_{col}"] = (
                create_feature_payload(
                    col,
                    monthly_metrics_df[col]
                )
            )

        return {
            "status": True,
            "result": json.dumps(payload, default=float),
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
    print(response["status"], response["result"])      # (the full JSON is long, so only status is printed)
    with open("predictor_scripts/output.json","a") as file:
        file.write(response["result"])
   
