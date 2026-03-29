import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
import plotly.express as px
# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="FinanceAI", page_icon="💰", layout="wide")

# =====================================================
# USER STORAGE
# =====================================================
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users_dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users_dict, f)

# =====================================================
# DATA PROCESSING
# =====================================================
def process_data(df):

    df = df.dropna()
    df["Date"] = pd.to_datetime(df["Date"])
    df["Description"] = df["Description"].str.lower()
    df["Amount"] = pd.to_numeric(df["Amount"])
    df["Type"] = df["Type"].str.strip()
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    categories = {
        "Salary": ["salary", "bonus"],
        "Food": ["swiggy", "zomato"],
        "Travel": ["uber", "ola", "irctc", "flight"],
        "Shopping": ["amazon", "shopping", "mall", "christmas", "diwali"],
        "Bills": ["electricity"],
        "EMI": ["emi"],
        "Fuel": ["petrol"],
        "Medical": ["hospital", "medical"],
        "Entertainment": ["netflix", "bookmyshow"],
        "Insurance": ["insurance"]
    }

    def categorize(desc):
        for cat, words in categories.items():
            for w in words:
                if w in desc:
                    return cat
        return "Others"

    df["Category"] = df["Description"].apply(categorize)

    expense_df = df[df["Type"] == "Debit"]
    mean_exp = expense_df["Amount"].mean()
    std_exp = expense_df["Amount"].std()

    df["Anomaly"] = False
    df.loc[
        (df["Type"] == "Debit") &
        (abs(df["Amount"] - mean_exp) > 2 * std_exp),
        "Anomaly"
    ] = True

    return df

# =====================================================
# DASHBOARD PAGE (ADVANCED)
# =====================================================
def dashboard_page(df):

    st.title("📊 Finance Overview")

    income = df[df["Type"] == "Credit"]["Amount"].sum()
    expense = abs(df[df["Type"] == "Debit"]["Amount"].sum())
    savings = income - expense
    savings_percent = (savings / income) * 100 if income != 0 else 0

    if savings_percent > 40:
        health = "Excellent 🟢"
    elif savings_percent > 20:
        health = "Moderate 🟡"
    else:
        health = "Risky 🔴"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income", f"₹{income:,.0f}")
    c2.metric("Expense", f"₹{expense:,.0f}")
    c3.metric("Savings", f"₹{savings:,.0f}")
    c4.metric("Savings %", f"{savings_percent:.1f}%")

    st.subheader("📊 Financial Health")
    st.success(health)

    # Monthly Trend
    st.subheader("📅 Monthly Expense Trend")

    monthly_expense = (
        df[df["Type"] == "Debit"]
        .groupby("Month")["Amount"]
        .sum()
        .abs()
        .sort_index()
    )

    if not monthly_expense.empty:
        fig3, ax3 = plt.subplots(figsize=(14,6))
        ax3.bar(monthly_expense.index, monthly_expense.values)
        ax3.set_title("Monthly Expenses")
        ax3.set_ylabel("Amount")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig3)

    # Month Selector
    st.subheader("📅 Select Month")
    months = sorted(df["Month"].unique())
    selected_month = st.selectbox("Choose Month", months)
    month_df = df[df["Month"] == selected_month]

    month_category = (
        month_df[month_df["Type"] == "Debit"]
        .groupby("Category")["Amount"]
        .sum()
        .abs()
    )

    st.subheader("📊 Monthly Category Analysis")

    colA, colB = st.columns(2)

    with colA:
        if not month_category.empty:
            fig2, ax2 = plt.subplots(figsize=(7,5))
            ax2.bar(month_category.index, month_category.values)
            ax2.set_title("Category Spending")
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig2)

    with colB:
        if not month_category.empty:
            fig, ax = plt.subplots(figsize=(7,5))
            ax.pie(
                month_category,
                labels=month_category.index,
                autopct="%1.1f%%",
                startangle=90,
                textprops={'fontsize':8},
                wedgeprops={"edgecolor": "white"}
            )
            ax.set_title("Spending Distribution")
            plt.tight_layout()
            st.pyplot(fig)

    # Top 3 Anomalies
    st.subheader("🚨 Top 3 Unusual Transactions")

    month_anomalies = month_df[month_df["Anomaly"] == True]
    top3 = month_anomalies.reindex(
        month_anomalies["Amount"].abs().sort_values(ascending=False).index
    ).head(3)

    if not top3.empty:
        st.dataframe(top3[["Date", "Description", "Amount", "Category"]], use_container_width=True)
    else:
        st.success("No major anomalies 🎉")

    # Smart Suggestions
    st.subheader("💡 Smart Suggestions")

    month_income = month_df[month_df["Type"] == "Credit"]["Amount"].sum()
    month_expense = abs(month_df[month_df["Type"] == "Debit"]["Amount"].sum())

    if month_expense > 0:
        food = month_category.get("Food", 0)
        emi = month_category.get("EMI", 0)

        if food / month_expense > 0.3:
            st.info("🍔 Food spending is high this month.")

        if emi / month_expense > 0.4:
            st.info("🏦 EMI burden is high.")

        if month_income > 0:
            saving = month_income - month_expense
            percent = (saving / month_income) * 100
            if percent < 20:
                st.warning("💰 Low monthly savings.")

        if not month_anomalies.empty:
            st.warning("⚠️ Unusual transactions detected.")

        st.success("📊 Keep tracking your spending!")

    st.subheader("📋 All Detected Anomalies")
    st.dataframe(
        df[df["Anomaly"] == True][["Date", "Description", "Amount", "Category", "Month"]],
        use_container_width=True
    )

# =====================================================
# TRANSACTIONS PAGE
# =====================================================
def transactions_page(df):

    st.title("📋 Transactions")

    col1, col2 = st.columns(2)

    with col1:
        type_filter = st.selectbox("Transaction Type", ["All", "Credit", "Debit"])

    with col2:
        category_filter = st.selectbox(
            "Category",
            ["All"] + sorted(df["Category"].unique().tolist())
        )

    filtered_df = df.copy()

    if type_filter != "All":
        filtered_df = filtered_df[filtered_df["Type"] == type_filter]

    if category_filter != "All":
        filtered_df = filtered_df[filtered_df["Category"] == category_filter]

    st.dataframe(filtered_df, use_container_width=True)

# =====================================================
# SMART NEXT MONTH PREDICTION
# =====================================================
def smart_next_month_prediction(df):

    st.subheader("📈 Smart Next Month Prediction")

    # Ensure Date is datetime
    df["Date"] = pd.to_datetime(df["Date"])

    # Create Year-Month column
    df["YearMonth"] = df["Date"].dt.to_period("M")

    # Monthly category summary
    monthly_cat = df.groupby(["YearMonth", "Category"])["Amount"].sum().reset_index()

    # Get last 3 months
    last_months = monthly_cat["YearMonth"].unique()[-3:]
    recent_data = monthly_cat[monthly_cat["YearMonth"].isin(last_months)]

    predictions = {}
    explanation = []

    categories = recent_data["Category"].unique()

    for cat in categories:
        cat_data = recent_data[recent_data["Category"] == cat]["Amount"].values

        if len(cat_data) < 2:
            pred = cat_data.mean()
        else:
            # Trend detection
            growth = (cat_data[-1] - cat_data[0]) / cat_data[0]

            if growth > 0.15:
                pred = cat_data[-1] * 1.10
                explanation.append(f"{cat} is increasing 📈")
            elif growth < -0.15:
                pred = cat_data[-1] * 0.95
                explanation.append(f"{cat} is decreasing 📉")
            else:
                pred = cat_data.mean()

        predictions[cat] = round(pred, 2)

    total_prediction = sum(predictions.values())
    

    # Risk Level
    avg_monthly = df.groupby("YearMonth")["Amount"].sum().mean()

    if total_prediction > avg_monthly * 1.2:
        risk = "🔴 High Risk"
    elif total_prediction > avg_monthly:
        risk = "🟡 Medium Risk"
    else:
        risk = "🟢 Low Risk"

    # Display Output
    st.markdown("### 📊 AI Forecast Result")
    st.success(f"📈 Expected Next Month Expense: ₹{round(total_prediction,2)}")
    st.warning(f"Risk Level: {risk}")

    st.write("### Category-wise Prediction")
    pred_df = pd.DataFrame(predictions.items(), columns=["Category", "Predicted Amount"])
    st.dataframe(pred_df, use_container_width=True)

    # Future Pie Chart
    st.write("### 🥧 Predicted Expense Distribution")
    fig = px.pie(pred_df, names="Category", values="Predicted Amount")
    st.plotly_chart(fig, use_container_width=True)

    if explanation:
        st.info("Trend Insights: " + ", ".join(explanation))

# =====================================================
# INSIGHTS PAGE
# =====================================================
def insights_page(df):

    st.title("📈 Financial Insights")

    total_transactions = len(df)
    total_credit = df[df["Type"] == "Credit"]["Amount"].sum()
    total_debit = abs(df[df["Type"] == "Debit"]["Amount"].sum())

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Transactions", total_transactions)
    col2.metric("Total Credit", f"₹{total_credit:,.0f}")
    col3.metric("Total Debit", f"₹{total_debit:,.0f}")

    st.markdown("---")

    st.subheader("💡 Basic Insights")

    if total_credit > 0:
        saving_rate = ((total_credit - total_debit) / total_credit) * 100

        if saving_rate > 40:
            st.success("Excellent saving habit 💚")
        elif saving_rate > 20:
            st.info("Moderate saving habit 💛")
        else:
            st.warning("Low savings ⚠️")

    anomaly_count = df["Anomaly"].sum()

    if anomaly_count > 0:
        st.warning(f"{anomaly_count} unusual transactions detected 🚨")
    else:
        st.success("No anomalies detected 🎉")

# =====================================================
# SESSION STATE INIT
# =====================================================
if "users" not in st.session_state:
    st.session_state.users = load_users()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

if "df" not in st.session_state:
    st.session_state.df = None

if "page" not in st.session_state:
    st.session_state.page = "Login"

# =====================================================
# AUTH PAGES
# =====================================================
def register_page():
    st.title("📝 Create Account")

    new_username = st.text_input("Choose Username")
    new_password = st.text_input("Choose Password", type="password")

    if st.button("Register"):
        if new_username in st.session_state.users:
            st.error("Username already exists!")
        elif new_username == "" or new_password == "":
            st.warning("Please fill all fields.")
        else:
            st.session_state.users[new_username] = new_password
            save_users(st.session_state.users)
            st.success("Account created successfully!")
            st.session_state.page = "Login"
            st.rerun()

def login_page():
    st.title("🔐 Login to FinanceAI")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in st.session_state.users and \
           st.session_state.users[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid Credentials")

    if st.button("Go to Register"):
        st.session_state.page = "Register"
        st.rerun()
# =====================================================
# DATA PROCESSING
# =====================================================
def process_data(df):
    df = df.dropna()
    df["Date"] = pd.to_datetime(df["Date"])
    df["Description"] = df["Description"].str.lower()
    df["Amount"] = pd.to_numeric(df["Amount"])
    df["Type"] = df["Type"].str.strip()
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    categories = {
        "Salary": ["salary", "bonus"],
        "Food": ["swiggy", "zomato"],
        "Travel": ["uber", "ola", "irctc", "flight"],
        "Shopping": ["amazon", "shopping", "mall"],
        "Bills": ["electricity"],
        "EMI": ["emi"],
        "Fuel": ["petrol"],
        "Medical": ["hospital", "medical"],
        "Entertainment": ["netflix", "bookmyshow"],
        "Insurance": ["insurance"]
    }

    def categorize(desc):
        for cat, words in categories.items():
            for w in words:
                if w in desc:
                    return cat
        return "Others"

    df["Category"] = df["Description"].apply(categorize)

    expense_df = df[df["Type"] == "Debit"]
    mean_exp = expense_df["Amount"].mean()
    std_exp = expense_df["Amount"].std()

    df["Anomaly"] = False
    df.loc[
        (df["Type"] == "Debit") &
        (abs(df["Amount"] - mean_exp) > 2 * std_exp),
        "Anomaly"
    ] = True

    return df


def upload_page():
    st.title(f"📂 Welcome, {st.session_state.username}")
    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        df = process_data(df)
        st.session_state.df = df
        st.session_state.file_uploaded = True
        st.success("File uploaded successfully!")
        st.rerun()

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.file_uploaded = False
    st.session_state.df = None
    st.session_state.page = "Login"
    st.rerun()

# =====================================================
# PREMIUM PAGE (ADDED GOAL SYSTEM)
# =====================================================
def premium_page(df):

    st.title("💎 Premium Dashboard")

    if st.button("⬅ Back to Free Dashboard"):
        st.session_state.premium_active = False
        st.rerun()

    st.markdown("---")

    # ---------- Weighted Prediction ----------
    st.subheader("🔮 Smart Next Month Analysis (Weighted Average)")

    monthly_expense = (
        df[df["Type"] == "Debit"]
        .groupby("Month")["Amount"]
        .sum()
        .abs()
        .sort_index()
    )

    if len(monthly_expense) >= 3:
        last3 = monthly_expense.tail(3).values
        predicted = 0.5 * last3[2] + 0.3 * last3[1] + 0.2 * last3[0]

        st.success(f"📈 Predicted Next Month Expense: ₹{predicted:,.0f}")

        last_month = last3[2]
        if predicted > last_month:
            st.warning("⚠️ Spending trend is increasing.")
        else:
            st.info("✅ Spending trend is stable or decreasing.")
    else:
        st.info("Not enough data (minimum 3 months required).")

    # ---------- AI Saving System ----------
    st.markdown("---")
    st.subheader("💰 AI Saving Improvement System (Last Month Analysis)")

    if len(monthly_expense) >= 1:

        last_month_name = monthly_expense.index[-1]
        last_month_df = df[df["Month"] == last_month_name]
        last_month_expense_df = last_month_df[last_month_df["Type"] == "Debit"]

        total_last_month_expense = abs(last_month_expense_df["Amount"].sum())

        category_last_month = (
            last_month_expense_df
            .groupby("Category")["Amount"]
            .sum()
            .abs()
        )

        suggestions = []
        total_potential_saving = 0

        for cat, amt in category_last_month.items():
            percent = (amt / total_last_month_expense) * 100 if total_last_month_expense > 0 else 0

            if percent > 25:
                reduction = amt * 0.15
                new_target = amt - reduction
                total_potential_saving += reduction

                suggestions.append({
                    "Category": cat,
                    "Current Spending": f"₹{amt:,.0f}",
                    "Suggested Target": f"₹{new_target:,.0f}",
                    "Potential Saving": f"₹{reduction:,.0f}"
                })

        if suggestions:
            suggestion_df = pd.DataFrame(suggestions)
            st.dataframe(suggestion_df, use_container_width=True)
            st.success(f"💰 Total Potential Monthly Saving: ₹{total_potential_saving:,.0f}")
        else:
            st.success("✅ Your spending distribution looks healthy for last month.")

    # =====================================================
    # 🎯 Personalized Saving Goal System (NEW FEATURE)
    # =====================================================

    st.markdown("---")
    st.subheader("🎯 Personalized Saving Goal System")

    goal_name = st.text_input("Enter Goal Name (e.g., Bike, Trip, Laptop)")
    goal_amount = st.number_input("Target Amount (₹)", min_value=0)
    goal_months = st.number_input("Time to Achieve (Months)", min_value=1)

    if goal_amount > 0:

        required_monthly = goal_amount / goal_months
        st.info(f"💰 Required Monthly Saving: ₹{required_monthly:,.0f}")

        if len(monthly_expense) >= 1:
            last_month_name = monthly_expense.index[-1]
            last_month_df = df[df["Month"] == last_month_name]

            income_last_month = last_month_df[last_month_df["Type"] == "Credit"]["Amount"].sum()
            expense_last_month = abs(last_month_df[last_month_df["Type"] == "Debit"]["Amount"].sum())
            current_saving = income_last_month - expense_last_month

            st.write(f"📊 Current Monthly Saving: ₹{current_saving:,.0f}")

            if current_saving >= required_monthly:
                st.success("✅ Your goal is achievable within selected time.")
                progress = min(current_saving / required_monthly, 1.0)
                st.progress(progress)
            else:
                shortfall = required_monthly - current_saving
                st.warning(f"⚠️ You need ₹{shortfall:,.0f} more per month to reach this goal.")

                if current_saving > 0:
                    estimated_months = goal_amount / current_saving
                    st.info(f"📅 At current saving rate, you will reach goal in {estimated_months:.1f} months.")
    # =====================================================
    # 🚨 SMART ALERT SYSTEM (Premium Only)
    # =====================================================

    st.markdown("---")
    st.subheader("🚨 Smart Alerts")

    alerts_triggered = False

    if len(monthly_expense) >= 1:

        last_month_name = monthly_expense.index[-1]
        last_month_df = df[df["Month"] == last_month_name]

        income_last = last_month_df[last_month_df["Type"] == "Credit"]["Amount"].sum()
        expense_last = abs(last_month_df[last_month_df["Type"] == "Debit"]["Amount"].sum())
        saving_last = income_last - expense_last

        # 1️⃣ Low Savings Alert
        if income_last > 0:
            saving_rate = (saving_last / income_last) * 100
            if saving_rate < 20:
                st.warning("⚠️ Savings rate is critically low (<20%).")
                alerts_triggered = True

        # 2️⃣ High EMI Pressure Alert
        emi_spend = last_month_df[
            (last_month_df["Type"] == "Debit") &
            (last_month_df["Category"] == "EMI")
        ]["Amount"].abs().sum()

        if expense_last > 0 and (emi_spend / expense_last) > 0.40:
            st.warning("⚠️ High EMI burden detected (>40% of expenses).")
            alerts_triggered = True

        # 3️⃣ Lifestyle Overspending Alerts
        food_spend = last_month_df[
            (last_month_df["Type"] == "Debit") &
            (last_month_df["Category"] == "Food")
        ]["Amount"].abs().sum()

        shopping_spend = last_month_df[
            (last_month_df["Type"] == "Debit") &
            (last_month_df["Category"] == "Shopping")
        ]["Amount"].abs().sum()

        if expense_last > 0:
            if (food_spend / expense_last) > 0.35:
                st.warning("⚠️ Food spending unusually high.")
                alerts_triggered = True

            if (shopping_spend / expense_last) > 0.25:
                st.warning("⚠️ Shopping spending unusually high.")
                alerts_triggered = True

        # 4️⃣ Rising Trend Alert (reuse weighted logic)
        if len(monthly_expense) >= 3:
            last3 = monthly_expense.tail(3).values
            predicted = 0.5 * last3[2] + 0.3 * last3[1] + 0.2 * last3[0]
            if predicted > last3[2]:
                st.warning("⚠️ Overall expense trend is rising.")
                alerts_triggered = True

        # 5️⃣ Goal Risk Alert
        if goal_amount > 0 and len(monthly_expense) >= 1:
            required_monthly = goal_amount / goal_months
            if saving_last < required_monthly:
                st.warning("⚠️ Your financial goal is at risk under current saving pattern.")
                alerts_triggered = True

    if not alerts_triggered:
        st.success("✅ No major financial risks detected. You're doing well!")
    # =====================================================
    # 📊 FUTURE WEALTH PROJECTION (Compound Growth)
    # =====================================================

    st.markdown("---")
    st.subheader("📊 Future Wealth Projection")

    if len(monthly_expense) >= 1:

        projection_years = st.slider("Select Projection Years", 1, 20, 5)
        expected_return = st.slider("Expected Annual Return (%)", 1, 20, 8)

        if saving_last > 0:

            months = projection_years * 12
            monthly_rate = (expected_return / 100) / 12

            # Compound Future Value of Monthly Investment (SIP Formula)
            future_value = saving_last * (((1 + monthly_rate) ** months - 1) / monthly_rate)

            simple_value = saving_last * 12 * projection_years

            st.write(f"💰 Current Monthly Saving: ₹{saving_last:,.0f}")

            st.info(f"Without Investment Growth: ₹{simple_value:,.0f}")
            st.success(f"With {expected_return}% Annual Return: ₹{future_value:,.0f}")

        else:
            st.warning("⚠️ No monthly savings available for projection.")
# =====================================================
# MAIN ROUTING
# =====================================================

if not st.session_state.logged_in:

    if st.session_state.page == "Register":
        register_page()
    else:
        login_page()

else:

    if not st.session_state.file_uploaded:
        upload_page()

    else:

        st.sidebar.title("💰 FinanceAI")
        st.sidebar.write(f"Logged in as: {st.session_state.username}")

        # Initialize premium flag
        if "premium_active" not in st.session_state:
            st.session_state.premium_active = False

        # Normal Navigation
        selected_page = st.sidebar.radio(
            "Navigation",
            ["Dashboard", "Transactions", "Insights"]
        )

        # Premium Button
        if st.sidebar.button("👑 Premium", use_container_width=True):
            st.session_state.premium_active = True
            st.rerun()

        # Logout
        if st.sidebar.button("Logout"):
            logout()

        # If Premium is active
        if st.session_state.premium_active:
            premium_page(st.session_state.df)

        else:
            if selected_page == "Dashboard":
                dashboard_page(st.session_state.df)

            elif selected_page == "Transactions":
                transactions_page(st.session_state.df)

            elif selected_page == "Insights":
                insights_page(st.session_state.df)