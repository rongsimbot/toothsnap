# ToothSnap - Dentist Directory & E-Commerce Platform

**Find dentists in your area that accept your insurance, and shop for dental products.**

## 🦷 Features

### Current (v1.0 - Dentist Directory)
- ✅ **Dentist Search** - Search by city, state, and insurance provider
- ✅ **Insurance Matching** - Filter dentists by accepted insurance (Aetna, Cigna, United Healthcare, Delta Dental, MetLife)
- ✅ **Rating System** - View dentist ratings and reviews
- ✅ **Detailed Profiles** - Contact info, address, accepted insurance
- ✅ **PostgreSQL Backend** - Fast, reliable database

### Coming Soon (v2.0 - E-Commerce)
- 🛒 **Product Catalog** - Browse dental care products (toothbrushes, whitening kits, etc.)
- 💳 **Shopify Integration** - Secure checkout and payment processing
- 📦 **Order Management** - Track orders and shipping
- 🤖 **AI Product Management** - Manage products via agent commands (mcp.zipper)

## 🛠 Tech Stack

**Backend:**
- Flask (Python 3.x)
- PostgreSQL
- Shopify Storefront API (coming soon)

**Frontend:**
- HTML5/CSS3
- Responsive design
- Modern gradient UI

**Deployment:**
- Azure (planned)
- Current: Windows GPU Server (DESKTOP-EC24FP3)

## 📦 Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/simrobotics/toothsnap.git
cd toothsnap

# Install dependencies
pip install flask psycopg2-binary

# Configure database
# Edit app.py with your PostgreSQL credentials

# Run development server
python app.py
```

Server runs on `http://localhost:8080`

## 🗄 Database Schema

### Tables:
1. **dentists** - Dentist profiles (name, practice, address, rating)
2. **insurance_providers** - Insurance companies
3. **dentist_insurance** - Many-to-many mapping

## 🚀 Roadmap

### Phase 1: Repository & Code Review ✅
- [x] Create GitHub repository
- [x] Document existing features
- [x] Review dentist directory functionality

### Phase 2: E-Commerce Integration (Week 1)
- [ ] Shopify account setup
- [ ] Product catalog design
- [ ] Shopify Storefront API integration
- [ ] Custom product display pages

### Phase 3: Azure Deployment (Week 2)
- [ ] Azure App Service configuration
- [ ] PostgreSQL migration to Azure
- [ ] SSL/Domain setup
- [ ] Production deployment

### Phase 4: AI Product Management
- [ ] mcp.zipper integration
- [ ] Agent-based product creation
- [ ] Inventory automation
- [ ] Pricing management

## 👥 Team

**Developer:** SimCoder (AI Agent)  
**Product Manager:** Ronnie Gaines  
**Coordinator:** Simbot (Main Agent)  
**Company:** SimRobotics Corp

## 📄 License

Proprietary - SimRobotics Corp © 2026

## 📞 Contact

For questions or support, contact: ronnie@simrobotics.com
