import os
import re
import json
import uuid
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple

import pandas as pd
import warnings

warnings.filterwarnings(
    "ignore",
    message="Converting to PeriodArray/Index representation will drop timezone information.*"
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("aa_feature_extraction")

AA_NAMESPACE = "http://homecredit.net/rcm/cbp/accountaggregator"
NS = {"acc": AA_NAMESPACE}

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

DISABLED_FEATURES = {
    "cash_withdrawal_amount",
    "cash_withdrawal_count",
    "credit_card_payment_amount",
    "credit_card_payment_count",
    "emi_debit_amount",
    "emi_debit_count",
    "investment_credit_amount",
    "investment_debit_amount",
    "loan_credit_amount",
    "loan_credit_count",
    "penalty_amount",
    "penalty_count",
    "salary_credit_amount",
    "single_account_max_credit_amount",
    "single_account_max_debit_amount",
}

DATA_KEY_OVERRIDES = {
    "maximum_balance": "max_balances",
    "minimum_balance": "min_balances",
    "days_since_max_balance": "days_since_max_balance",
    "eod_balance_count_less_than_1000": "eod_balance_count_less_than_1000",
    "avg_balance_in_last_7days": "avg_balances_last_7_days",
    "last_7days_max_balance": "last_7_days_max_balances",
    "last_7days_min_balance": "last_7_days_min_balances",
    "total_third_party_credit_amount": "grouped_total_third_party_credit_amount",
    "single_account_max_credit_amount": "grouped_single_account_max_credit_amount",
    "single_account_max_debit_amount": "grouped_single_account_max_debit_amount",
}


def data_key_for(column_name):
    return DATA_KEY_OVERRIDES.get(column_name, f"{column_name}s")


def to_ddmmyyyy(date_text):
    if not date_text:
        return ""
    try:
        return pd.Timestamp(date_text).strftime("%d-%m-%Y")
    except (ValueError, TypeError):
        return date_text


def _local_name(tag: str) -> str:
    if tag and "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag or ""


def _find(node, tag: str, descendants: bool = False):
    """Find a child by the AA namespace, then by local name.

    Scorecards vectors leave account, Summary, and Transactions un-namespaced
    while binding xmlns:acc only on those elements.
    """
    if node is None:
        return None
    path = f".//acc:{tag}" if descendants else f"acc:{tag}"
    element = node.find(path, NS)
    if element is not None:
        return element
    search = node.iter() if descendants else list(node)
    for child in search:
        if _local_name(child.tag) == tag:
            return child
    return None


class AccountAggregatorParser:

    def __init__(self, xml_source):
        """Parse Account Aggregator XML from bytes, an XML string, or a file path."""
        logger.info("Parsing XML source type: %s", type(xml_source).__name__)
        self.root = self._parse_root(xml_source)
        self.account = self._find_account_item(self.root)

        if self.account is None:
            logger.error("Account node not found in XML")
            raise ValueError("Account node not found in XML.")

    @staticmethod
    def _parse_root(xml_source):
        if isinstance(xml_source, (bytes, bytearray)):
            return ET.fromstring(xml_source)
        if isinstance(xml_source, str):
            stripped = xml_source.lstrip()
            if stripped.startswith("<"):
                return ET.fromstring(xml_source)
            xml_path = Path(xml_source)
            if not xml_path.exists():
                raise FileNotFoundError(f"XML file not found: {xml_source}")
            return ET.parse(xml_path).getroot()
        if isinstance(xml_source, Path):
            if not xml_source.exists():
                raise FileNotFoundError(f"XML file not found: {xml_source}")
            return ET.parse(xml_source).getroot()
        raise TypeError(f"Unsupported XML source type: {type(xml_source).__name__}")
 
    @staticmethod
    def _find_account_item(root):
        """Find the account item that has a direct Transactions child.

        Namespaced GetRawDataResponse files and un-namespaced scorecards
        vectors both contain a holder item that must not be selected.
        """
        for elem in root.iter():
            if _local_name(elem.tag) != "item":
                continue
            for child in list(elem):
                if _local_name(child.tag) == "Transactions":
                    return elem
        return None

    @staticmethod
    def get_text(node, tag: str):
        if node is None:
            return None
        element = node.find(f"acc:{tag}", NS)
        if element is None:
            for child in list(node):
                if _local_name(child.tag) == tag:
                    element = child
                    break
        return element.text.strip() if element is not None and element.text else None

    def extract_all_other_info(self) -> pd.DataFrame:
        holder = self.account.find(".//acc:Holder/acc:item", NS)
        summary = _find(self.account, "Summary")
        transactions = _find(self.account, "Transactions", descendants=True)

        data = {
            "end_date": to_ddmmyyyy(self.get_text(transactions, "endDate")),
            "account_number": self.get_text(self.account, "maskedAccountNumber"),
            "account_type": self.get_text(summary, "type") or "",
            "mobile": self.get_text(holder, "mobile"),
            "full_address": self.get_text(holder, "address"),
            "latest_balance": self.get_text(summary, "currentBalance"),
            "ifsc_code": self.get_text(summary, "ifscCode"),
            "full_name": self.get_text(holder, "name"),
            "account_open_date": to_ddmmyyyy(self.get_text(summary, "openingDate")),
            "dob": to_ddmmyyyy(self.get_text(holder, "dob")),
            "bank_name": self.get_text(self.account, "bank"),
            "micr_code": self.get_text(summary, "micrCode") or "",
            "link_reference_no": self.get_text(self.account, "linkReferenceNumber"),
            "email": self.get_text(holder, "email"),
            "tracking_id": "",
            "start_date": to_ddmmyyyy(self.get_text(transactions, "startDate")),
        }

        return pd.DataFrame([data])

    def extract_statement_period(self) -> Tuple[pd.Timestamp, pd.Timestamp]:
        transactions = _find(self.account, "Transactions", descendants=True)
        start_text = self.get_text(transactions, "startDate")
        end_text = self.get_text(transactions, "endDate")

        if not start_text or not end_text:
            raise ValueError("startDate / endDate missing from Transactions node in XML.")

        try:
            start_date = pd.Timestamp(start_text)
            end_date = pd.Timestamp(end_text)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Could not parse statement period from XML: {e}")

        if start_date > end_date:
            logger.error("startDate (%s) is after endDate (%s) in XML.", start_date, end_date)
            raise ValueError(f"startDate ({start_date}) is after endDate ({end_date}) in XML.")

        logger.info("Statement period: %s to %s", start_date.date(), end_date.date())
        return start_date, end_date

    def extract_transactions(self) -> pd.DataFrame:
        transactions = self.account.findall(".//acc:Transaction/acc:item", NS)
        logger.info("Extracted %d transactions from XML", len(transactions))

        columns = [
            "txn_id", "mode", "type", "amount", "narration", "reference",
            "value_date", "transaction_timestamp", "transactional_balance",
        ]

        if not transactions:
            return pd.DataFrame(columns=columns)

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
                "transaction_timestamp": self.get_text(txn, "transactionTimestamp"),
                "transactional_balance": self.get_text(txn, "currentBalance"),
            })

        df = pd.DataFrame(rows)
        self._transform_transaction_data(df)
        return df

    @staticmethod
    def _transform_transaction_data(df: pd.DataFrame):
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["transactional_balance"] = pd.to_numeric(df["transactional_balance"], errors="coerce")
        df["value_date"] = pd.to_datetime(df["value_date"], errors="coerce")
        df["transaction_timestamp"] = pd.to_datetime(df["transaction_timestamp"], utc=True, errors="coerce")

        missing_amount = df["amount"].isna().sum()
        missing_balance = df["transactional_balance"].isna().sum()
        missing_timestamp = df["transaction_timestamp"].isna().sum()
        if missing_amount or missing_balance or missing_timestamp:
            raise ValueError(
                f"Transactions with unparseable amount ({missing_amount}), "
                f"balance ({missing_balance}) or timestamp ({missing_timestamp}) found in XML."
            )

        df["is_credit"] = df["type"].eq("CREDIT")
        df["is_debit"] = df["type"].eq("DEBIT")


class TransactionClassifier:

    def normalize_text(self, text):
        if pd.isna(text):
            return ""
        text = str(text).upper().strip()
        return re.sub(r"\s+", " ", text)

    def identify_channel(self, mode, narration):
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
        ignore = {"UPI", "UPIAB", "UPIAR", "CR", "DR", "IMPS", "RTGS", "NEFT", "P2A", "P2M", "REV", "TRANSFER"}

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

    def classify(self, df):
        df = df.copy()

        if df.empty:
            df["narration_clean"] = pd.Series(dtype="object")
            df["payment_channel"] = pd.Series(dtype="object")
            df["counterparty"] = pd.Series(dtype="object")
            return df

        df["narration_clean"] = df["narration"].apply(self.normalize_text)

        df["payment_channel"] = df.apply(
            lambda row: self.identify_channel(row["mode"], row["narration_clean"]),
            axis=1
        )

        df["counterparty"] = df["narration_clean"].apply(self.extract_counterparty)

        return df


class BalanceAnalytics:

    @staticmethod
    def _txn_day(df: pd.DataFrame) -> pd.Series:
        return df["transaction_timestamp"].dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()

    @staticmethod
    def create_daily_balance_series(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
        if df.empty:
            raise ValueError("Cannot build a daily balance series from zero transactions.")

        df = df.sort_values("transaction_timestamp", kind="stable").copy()
        df["day"] = BalanceAnalytics._txn_day(df)

        last_of_day = df.groupby("day")["transactional_balance"].last()
        first_of_day = df.groupby("day")["transactional_balance"].first()

        first_txn = df.iloc[0]
        carry = (
            first_txn["transactional_balance"] + first_txn["amount"]
            if first_txn["type"] == "DEBIT"
            else first_txn["transactional_balance"] - first_txn["amount"]
        )

        records = []
        for day in pd.date_range(start=start_date, end=end_date, freq="D"):
            if day in last_of_day.index:
                records.append((day, last_of_day[day], False))
                # carry = first_of_day[day]
                carry = last_of_day[day]

            else:
                records.append((day, carry, True))

        daily_df = pd.DataFrame(records, columns=["day", "eod_balance", "is_filler"])
        daily_df["year_month"] = daily_df["day"].dt.to_period("M")
        
        return daily_df

    @staticmethod
    def monthly_metrics(df: pd.DataFrame, daily_df: pd.DataFrame, end_date) -> pd.DataFrame:
        end_date = pd.Timestamp(end_date)

        df = df.copy()
        df["day"] = BalanceAnalytics._txn_day(df)
        df["year_month"] = df["day"].dt.to_period("M")

        results = []

        for year_month, daily_m in daily_df.groupby("year_month"):
            if daily_m.empty:
                continue

            txn_m = df[df["year_month"] == year_month]

            txn_balances = txn_m["transactional_balance"]
            fillers = daily_m.loc[daily_m["is_filler"], "eod_balance"]
            eod = daily_m["eod_balance"]

            all_rows = pd.concat([txn_balances, fillers])
            average_balance = all_rows.mean() if len(all_rows) else 0
            maximum_balance = all_rows.max() if len(all_rows) else 0
            minimum_balance = all_rows.min() if len(all_rows) else 0
          
        
            month_end_balance = (
                daily_m["eod_balance"].iloc[-1]
                if len(daily_m)
                else 0
            )

            median_eod_balance = eod.median()
        
            eod_balance_count_less_than_1000 = int((eod < 1000).sum())

            if len(txn_m):
                max_balance_day = txn_m.loc[txn_m["transactional_balance"].idxmax(), "day"]
                days_since_max_balance = (end_date - max_balance_day).days
            else:
                days_since_max_balance = 0

            window_start = year_month.start_time.normalize() + pd.Timedelta(days=year_month.days_in_month - 7)
            daily_7 = daily_m[daily_m["day"] >= window_start]

            rows_7 = pd.concat([
                txn_m.loc[txn_m["day"] >= window_start, "transactional_balance"],
                daily_7.loc[daily_7["is_filler"], "eod_balance"],
            ])

            avg_balance_in_last_7days = daily_7["eod_balance"].mean() if len(daily_7) else 0
            last_7days_max_balance = rows_7.max() if len(rows_7) else 0
            last_7days_min_balance = rows_7.min() if len(rows_7) else 0

            results.append({
                "year_month": year_month,
                "average_balance": round(average_balance, 2),
                "maximum_balance":round(maximum_balance,2),
                "minimum_balance": round(minimum_balance,2),
                "month_end_balance": round(month_end_balance,2),
                "days_since_max_balance": int(days_since_max_balance),
                "eod_balance_count_less_than_1000": eod_balance_count_less_than_1000,
                "median_eod_balance": round(median_eod_balance, 2),
                "avg_balance_in_last_7days": round(avg_balance_in_last_7days, 2),
                "last_7days_max_balance": round(last_7days_max_balance,2),
                "last_7days_min_balance": round(last_7days_min_balance,2)
            })

        if not results:
            raise ValueError("No monthly balance metrics could be computed for the statement period.")

        return pd.DataFrame(results).sort_values("year_month", ascending=False).reset_index(drop=True)


class TransactionFeatureGenerator:

    def generate(self, df: pd.DataFrame, start_date=None, end_date=None) -> pd.DataFrame:
        columns = [
            "credit_count", "debit_count", "credit_amount", "debit_amount",
            "maximum_credit_amount", "maximum_debit_amount",
            "upi_credit_count", "upi_debit_count", "upi_credit_amount", "upi_debit_amount",
            "total_third_party_credit_amount",
        ] + sorted(DISABLED_FEATURES)

        if df.empty:
            if start_date is None or end_date is None:
                raise ValueError("No transactions found in XML and no statement period given to fill months from.")
            logger.warning("No transactions found in XML; all features will be 0 or null.")
            all_months = pd.period_range(start_date, end_date, freq="M")
            features = pd.DataFrame(0, index=all_months, columns=columns)
            features.index.name = "year_month"
            for col in DISABLED_FEATURES:
                features[col] = None
            return features.reset_index().sort_values("year_month", ascending=False).reset_index(drop=True)

        df = df.copy()
        df["year_month"] = df["transaction_timestamp"].dt.to_period("M")
        grouped = df.groupby("year_month")

        features = pd.DataFrame()

        features["credit_count"] = grouped.apply(lambda x: (x["type"] == "CREDIT").sum())
        
        features["debit_count"] = grouped.apply(lambda x: (x["type"] == "DEBIT").sum())
        features["credit_amount"] = grouped.apply(lambda x: x.loc[x["type"] == "CREDIT", "amount"].sum().round(2))
        features["debit_amount"] = grouped.apply(lambda x: x.loc[x["type"] == "DEBIT", "amount"].sum().round(2))

        features["maximum_credit_amount"] = grouped.apply(
            lambda x: x.loc[x["type"] == "CREDIT", "amount"].max()
        ).fillna(0).round(2)
        features["maximum_debit_amount"] = grouped.apply(
            lambda x: x.loc[x["type"] == "DEBIT", "amount"].max()
        ).fillna(0).round(2)

        features["upi_credit_count"] = grouped.apply(
            lambda x: ((x["payment_channel"] == "UPI") & (x["type"] == "CREDIT")).sum()
        )
        features["upi_debit_count"] = grouped.apply(
            lambda x: ((x["payment_channel"] == "UPI") & (x["type"] == "DEBIT")).sum()
        )
        features["upi_credit_amount"] = grouped.apply(
            lambda x: x.loc[(x["payment_channel"] == "UPI") & (x["type"] == "CREDIT"), "amount"].sum()
        ).round(2)
        features["upi_debit_amount"] = grouped.apply(
            lambda x: x.loc[(x["payment_channel"] == "UPI") & (x["type"] == "DEBIT"), "amount"].sum()
        ).round(2)

        features["total_third_party_credit_amount"] = grouped.apply(
            lambda x: x.loc[(x["type"] == "CREDIT") & x["counterparty"].notna(), "amount"].sum()
        ).round(2)

        if start_date is not None and end_date is not None:
            all_months = pd.period_range(start_date, end_date, freq="M")
            features = features.reindex(all_months, fill_value=0)
            features.index.name = "year_month"

        for col in DISABLED_FEATURES:
            features[col] = None

        logger.info("Transaction-level features computed for %d months (%d disabled/null)",
                    len(features), len(DISABLED_FEATURES))

     
        features=features.reset_index().sort_values("year_month", ascending=False).reset_index(drop=True)
        return features


def _feature_item(values, data_key):
    return [{
        "data": {data_key: [None if v is None or pd.isna(v) else float(v) for v in values]},
        "id": str(uuid.uuid4()),
        "config": {"period": len(values), "sortby": "decreasing", "grouping": "monthly"},
    }]



def build_feature_tables(xml_path):
    parser = AccountAggregatorParser(xml_path)

    df_customer = parser.extract_all_other_info()
    start_date, end_date = parser.extract_statement_period()

    transactions_df = parser.extract_transactions()

    classifier = TransactionClassifier()
    classified_df = classifier.classify(transactions_df)

    feature_generator = TransactionFeatureGenerator()
    transactional_features_df = feature_generator.generate(classified_df, start_date, end_date)

    if classified_df.empty:
        raise ValueError(f"No transactions found in {xml_path}; cannot compute balance features.")

    daily_df = BalanceAnalytics.create_daily_balance_series(classified_df, start_date=start_date, end_date=end_date)
    monthly_metrics_df = BalanceAnalytics.monthly_metrics(classified_df, daily_df, end_date=end_date)
    logger.info("Balance features computed for %d months", len(monthly_metrics_df))

    return df_customer, transactional_features_df, monthly_metrics_df


def compute(data) -> dict:
    """Scorecards entrypoint. The engine passes {'message': <xml bytes|str>}."""
    xml_source = data["message"] if isinstance(data, dict) else data
    logger.info("Request received: build_expected_response(source_type=%s)", type(xml_source).__name__)
    try:
        df_customer, transactional_features_df, monthly_metrics_df = build_feature_tables(xml_source)

        parser = AccountAggregatorParser(xml_source)
        _, end_date = parser.extract_statement_period()
        link_reference_no = df_customer.iloc[0]["link_reference_no"]

        annotation = {
            "insight_type": "BANK_STATEMENT_ANNOTATIONS",
            "insight_group": "BANK_STATEMENT",
            "link_reference_no": link_reference_no,
            "reference_end_date": to_ddmmyyyy(str(end_date.date())),
        }

        for table in (transactional_features_df, monthly_metrics_df):
            for col in table.columns:
                if col == "year_month":
                    continue
                annotation[f"grouped_{col}"] = _feature_item(table[col], data_key_for(col))
        
        journey_id = "aa_analytics_home_credit_v1"
        transaction_id = str(uuid.uuid4())
        journey_transaction_id = f"EQ.GT.{uuid.uuid4()}#{journey_id}#{uuid.uuid4().hex}"

        logger.info("Response built successfully for transaction_id=%s", transaction_id)

        expected_response={
            "status": "SUCCESS",
            "message": "Success",
            "status_code": "success",
            "transaction_id": transaction_id,
            "journey_transaction_id": journey_transaction_id,
            "journey_id": journey_id,
            "data": {
                "insights": {"bank_statement_annotations": [annotation]},
                "keys": {"bank_statement": [df_customer.iloc[0].to_dict()]},
            },
        }

        result = json.loads(json.dumps(expected_response, default=float))
        return {"status": True, "result": result, "message": "OK", "version": "v3"}


    except Exception as e:
        logger.exception("Failed to build response")

        return {"status": False, "result": None, "message": str(e), "version": "v3"}




if __name__ == "__main__":
    xml_path = "GetRawResponse/Accountagg_cuid_102753192_skp_225505577.xml"
    logger.info("Script started for xml_path=%s", xml_path)

    response = compute(xml_path)
    logger.info("Script finished with status=%s message=%s", response["status"], response["message"])

    with open("data/output.json","a") as file:
        file.write(json.dumps(response))
