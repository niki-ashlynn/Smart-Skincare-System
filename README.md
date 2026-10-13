# 🧴 Smart Skincare Inventory Management System

### IoT-Based Inventory Monitoring for Beauty Clinics

**Python | Tkinter | Azure IoT Hub | Azure Cosmos DB | IoT | Cloud Computing**

A smart inventory management prototype designed for beauty clinics to monitor skincare product usage, stock levels, expiry dates and replacement requirements.

The project explores how IoT concepts, automated monitoring and cloud technologies can improve inventory visibility and support more sustainable product management.

Developed as part of the **Internet of Things (IoT) coursework — PSB602IT**, aligned with **United Nations Sustainable Development Goal 12: Responsible Consumption and Production**.

---

## 📌 Project Overview

Beauty clinics use a variety of skincare products for treatments and daily operations. Managing these products manually can become challenging, especially when tracking quantities, expiry dates, batch information and product consumption.

The Smart Skincare Inventory Management System was designed to address these challenges through a Python-based desktop application.

The system uses simulated product consumption to demonstrate how inventory data could be monitored and updated automatically in an IoT-enabled environment.

The prototype focuses on:

- Product inventory tracking
- Barcode and batch identification
- Stock level monitoring
- Product expiry management
- Automated usage simulation
- Low-stock and critical-stock identification
- Product replacement logic
- Inventory data visualisation

## 🎯 Project Objectives

1. Develop a smart inventory monitoring prototype for beauty clinics.
2. Track skincare products using barcode and batch information.
3. Monitor remaining product quantities and expiry dates.
4. Simulate product usage to demonstrate automated inventory updates.
5. Identify products requiring replacement.
6. Explore the use of Azure cloud technologies for inventory data management.
7. Support SDG 12 by addressing potential product waste and inefficient inventory practices.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core application logic and inventory processing |
| Tkinter | Desktop graphical user interface |
| Azure Cosmos DB | Cloud-based inventory data storage integration |
| Azure IoT Hub | IoT connectivity and communication architecture |
| Barcode Identification | Product and batch identification |
| Data Visualisation | Displaying inventory usage and remaining stock |
| VS Code | Application development and debugging |

**Note:** The system is an IoT prototype using simulated product usage. Physical sensor deployment and production-scale Azure integration are not claimed as completed implementations.

## ✨ Key Features

### 1. Product Inventory Management

The application maintains structured information about skincare products used in a beauty clinic.

Product attributes include:

- Product ID
- Barcode
- Brand and product name
- Product category
- Batch code
- Expiry date
- Initial product weight
- Current product weight
- Selling price
- Units sold
- Last used date
- Inventory status

These records allow individual products and batches to be monitored throughout their usage lifecycle.

### 2. Automated Product Usage Simulation

The prototype includes an automated simulation feature that demonstrates how product consumption could be tracked in an IoT environment.

- Simulates decreases in product quantities.
- Updates remaining product weight.
- Recalculates remaining stock percentages.
- Updates inventory status based on usage.
- Refreshes inventory information automatically.

The simulation represents potential IoT sensor readings rather than measurements collected from physical hardware.

### 3. Stock Level Monitoring

The system monitors remaining product quantities and classifies stock conditions.

| Status | Description |
|---|---|
| IN STOCK | Product has sufficient remaining quantity |
| MEDIUM | Product quantity has decreased |
| LOW | Product is approaching a low-stock condition |
| CRITICAL | Product quantity requires urgent attention |

Stock classifications help users identify products that may require monitoring or replenishment.

### 4. Expiry Date Monitoring

The system evaluates product expiry dates and identifies products approaching or exceeding their expiry.

Expiry classifications include:

- OK
- WARNING
- CRITICAL
- EXPIRED

This functionality is intended to support better product rotation and reduce the risk of expired skincare products remaining in active inventory.

### 5. Product Lifecycle Tracking

The prototype tracks product usage through different lifecycle states.

- NEW — Product has not yet been used.
- IN USE — Product is currently being consumed.
- USED — Product has been depleted.
- EXPIRED — Product has passed its expiry date.

Expired products are identified separately to support inventory review and replacement decisions.

### 6. Automated Replacement Logic

The system includes logic for creating replacement records when products become depleted or expire.

The replacement mechanism is designed to:

- Identify used or expired products.
- Trigger replacement record creation.
- Support continuity of inventory records.
- Reduce repetitive manual inventory updates.

This demonstrates how automation could support inventory replenishment workflows.

### 7. Inventory Dashboard and Visualisation

The desktop interface provides a structured view of product inventory.

The dashboard presents information such as:

- Product details and batch codes
- Remaining product weight
- Remaining stock percentage
- Inventory and expiry status
- Product usage information

The prototype also explores visualising product usage and remaining stock by batch.

## ☁️ Cloud and IoT Architecture

The project explores separating the application interface, inventory processing logic and cloud data management.

**Conceptual Architecture**

```text
Beauty Clinic Inventory
          |
          v
Simulated Product Usage
          |
          v
Python Application Logic
          |
          v
Inventory Status Processing
          |
          v
Azure Cosmos DB
(Cloud Data Storage)
          |
          v
Tkinter Inventory Dashboard
          |
          v
Stock Alerts & Replacement Logic
```

**Azure IoT Hub** is part of the proposed IoT architecture for supporting communication with connected devices in a future physical deployment.

The prototype currently demonstrates IoT-style monitoring through software simulation rather than live sensor measurements.

## ⚙️ System Workflow

1. **Product Registration**  
   Product information is recorded, including barcode, batch code, weight and expiry date.

2. **Inventory Monitoring**  
   The system displays the current product quantity and status.

3. **Usage Simulation**  
   Simulated consumption decreases the remaining product weight.

4. **Status Calculation**  
   Inventory conditions are recalculated using remaining quantities and expiry information.

5. **Inventory Updates**  
   The dashboard refreshes to display updated product information.

6. **Replacement Processing**  
   Products identified as depleted or expired can trigger replacement logic.

7. **Data Visualisation**  
   Inventory information can be presented through tables and batch-level usage visualisations.

## 🌱 Sustainable Development Goal 12

### Responsible Consumption and Production

This project was developed in alignment with **SDG 12**, which promotes sustainable consumption and production practices.

Beauty clinics may experience product waste when inventory is poorly monitored, products expire before use or replacement decisions are made without accurate stock information.

The proposed system addresses these concerns through:

**Reducing Product Waste**
- Monitoring expiry dates.
- Identifying unused or expiring products.
- Supporting better inventory rotation.

**Improving Resource Management**
- Tracking remaining product quantities.
- Monitoring product consumption.
- Identifying replacement requirements.

**Supporting Data-Driven Decisions**
- Providing structured inventory records.
- Presenting product usage information.
- Helping clinic staff identify potential stock management issues.

The system demonstrates potential sustainability benefits; actual waste reduction has not been measured in a live clinic environment.

## 💡 Skills Demonstrated

### Programming & Software Development
- Python application development
- Tkinter GUI design
- Application logic and automation
- Data validation and processing
- Debugging and testing

### Data Management
- Structured product records
- Inventory data organisation
- Stock calculations
- Batch-based tracking
- Database integration concepts

### Cloud & IoT
- Azure cloud architecture concepts
- Azure Cosmos DB integration design
- Azure IoT Hub concepts
- Simulated IoT monitoring
- Automated inventory workflows

### Analytical & Problem-Solving Skills
- Requirements analysis
- Inventory status classification
- Data visualisation
- Process automation
- Sustainability-focused system design

## 📈 Project Outcomes

The Smart Skincare Inventory Management System demonstrates how automated monitoring can be applied to inventory management within a beauty clinic.

The prototype provides a foundation for:

- Monitoring skincare product usage.
- Identifying products approaching expiry.
- Classifying inventory stock levels.
- Automating selected replacement workflows.
- Presenting inventory information through a graphical interface.

Through this project, I gained experience developing a Python-based management application, designing automated inventory logic and exploring cloud-based data management.

## 🚀 Future Improvements

Potential future developments include:

- Integration with physical weight sensors.
- Barcode scanning using dedicated hardware.
- Live telemetry through Azure IoT Hub.
- Production deployment of cloud-based inventory storage.
- Real-time alerts through email or mobile notifications.
- Predictive analytics for product demand and replenishment.
- Power BI dashboards for inventory trends.
- Multi-user access for clinic employees.
- Historical reporting for product consumption and waste.

## 👩🏻‍💻 Developer

**Thiri Myat Thwe**

BSc (Hons) Computing Science  
Coventry University | PSB Academy, Singapore

Aspiring Data Analyst | Data Science & Cloud Technology Enthusiast

📧 **Email:** thirimyatthwe40@gmail.com

🔗 **LinkedIn:** https://www.linkedin.com/in/thiri-myat-thwe-n1k1/

💻 **GitHub:** https://github.com/niki-ashlynn

---

*Smart Skincare Inventory Management System — PSB602IT Internet of Things Coursework | 2026*

*Exploring smarter inventory management through automation, data and sustainable technology.*

