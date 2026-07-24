# 🏥 Medicare Healthcare Systems Simulator

A GUI-based Python simulation application designed to model patient queuing dynamics, hospital doctor/clinic allocations, and triage urgency disciplines across standard queuing models ($M/M/s$, $M/G/s$, and $G/G/s$).

## Key Features
- **Queuing Systems Modeling:** Supports $M/M/s$, $M/G/s$, and $G/G/s$ multi-server queue models with configurable arrival ($\lambda$) and service ($\mu$) rates.
- **Statistical Distributions:** Generates synthetic arrivals and treatment times using Exponential, Normal, Uniform, Lognormal, and Gamma probability distributions.
- **Preemptive Triage Scheduling:** Simulates preemptive priority queue management to assign incoming high-urgency patients to active doctors.
- **Interactive GUI Dashboard:** Built with `ttkbootstrap` and `tkinter`, featuring patient data logs, KPI performance metrics ($L, L_q, W, W_q, \rho$), and embedded `matplotlib` Gantt timeline charts.

## Technologies Used
- **Language:** Python 3
- **GUI Framework:** Tkinter / `ttkbootstrap`
- **Data Visualization:** `matplotlib` (Embedded via `FigureCanvasTkAgg`)
- **Mathematics & Statistics:** `math`, `random`, `decimal`, `statistics`

## Installation & Running


1. Clone the repository:
   ```bash
 git clone https://github.com/aaliyanarif-99/medicare-queuing-simulator.git
   cd medicare-queuing-simulator
   ```

2. Install dependencies:
   ```bash
   pip install ttkbootstrap matplotlib
   ```
   
3. Run the application:
 ```bash
 python app.py
 ```
