# BillTrace Ledger — Smart Expense & Bill Management System

**Developed by — Sruthi Sureshkumar and Thaarini **

BillTrace Ledger is a full-stack expense and bill management platform designed to simplify personal financial tracking. It enables users to securely record income and expenses, organize transactions into categories, monitor spending habits, and visualize financial insights through an intuitive dashboard.

The application provides secure authentication, real-time financial summaries, and an easy-to-use interface for managing day-to-day expenses.

---

# Features

## User Features

* Secure user registration and login using JWT authentication
* Add, edit, and delete income and expense transactions
* Categorize transactions for better expense tracking
* View complete transaction history
* Dashboard displaying:

  * Total Income
  * Total Expenses
  * Current Balance
* Search and filter transactions
* Responsive interface for desktop and mobile devices

---

# Dashboard

The dashboard provides a quick overview of financial activity, including:

* Current account balance
* Income summary
* Expense summary
* Recent transactions
* Spending analytics and visualizations

---

# Tech Stack

| Layer          | Technology                                    |
| -------------- | --------------------------------------------- |
| Frontend       | React.js                                      |
| Backend        | Node.js, Express.js                           |
| Database       | MongoDB (Mongoose)                            |
| Authentication | JWT, bcryptjs                                 |
| API            | REST API                                      |
| Styling        | CSS / Bootstrap *(or Tailwind if applicable)* |

---

# Project Structure

```
billtrace-ledger/
├── client/
│   ├── public/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── context/
│       ├── services/
│       ├── assets/
│       └── App.js
│
├── server/
│   ├── controllers/
│   ├── middleware/
│   ├── models/
│   ├── routes/
│   ├── config/
│   ├── utils/
│   └── server.js
│
├── package.json
└── README.md
```

---

# Getting Started

## Prerequisites

* Node.js (v18 or later)
* MongoDB (Local or Atlas)
* npm

---

## 1. Clone the Repository

```bash
git clone https://github.com/sruthisureshkumar-arch/billtrace-ledger.git

cd billtrace-ledger
```

---

## 2. Backend Setup

```bash
cd server

npm install
```

Create a `.env` file:

```env
PORT=5000

MONGO_URI=your_mongodb_connection_string

JWT_SECRET=your_secret_key
```

Start the backend server:

```bash
npm start
```

or

```bash
node server.js
```

---

## 3. Frontend Setup

```bash
cd client

npm install

npm start
```

The frontend runs on:

```
http://localhost:3000
```

The backend runs on:

```
http://localhost:5000
```

---

# API Overview

| Method | Endpoint              | Description                |
| ------ | --------------------- | -------------------------- |
| POST   | /api/auth/register    | Register a new user        |
| POST   | /api/auth/login       | Login user                 |
| GET    | /api/transactions     | Fetch all transactions     |
| POST   | /api/transactions     | Add a transaction          |
| PUT    | /api/transactions/:id | Update a transaction       |
| DELETE | /api/transactions/:id | Delete a transaction       |
| GET    | /api/dashboard        | Retrieve dashboard summary |

---

# Security

* Passwords encrypted using **bcryptjs**
* JWT-based authentication
* Protected API routes
* User-specific financial records

---

# Future Improvements

* Monthly budget planning
* Bill payment reminders
* Recurring transactions
* CSV/Excel export
* PDF report generation
* Multi-currency support
* Dark mode
* Email notifications
* Expense analytics with charts
* AI-powered spending insights

---

# Screenshots

Add screenshots of the following pages:

* Login
* Register
* Dashboard
* Add Transaction
* Transaction History
* Analytics

---

# Author

**Sruthi Sureshkumar and Thaarini**

