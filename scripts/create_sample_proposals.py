"""
Creates sample business proposal PDFs in data/proposals/ for demo/testing.
Requires: fpdf2  (pip install fpdf2)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PROPOSALS = [
    {
        "filename": "software_development_proposal.pdf",
        "title": "Custom Software Development Proposal",
        "content": [
            ("Executive Summary",
             "TechSolutions Inc. proposes to develop a custom enterprise resource planning (ERP) "
             "system for MegaCorp Ltd. This cloud-based solution will integrate finance, HR, "
             "supply chain, and customer relationship management into a single platform."),
            ("Problem Statement",
             "MegaCorp currently operates with 7 disconnected legacy systems, resulting in "
             "data silos, manual re-entry errors, and 3+ hours of daily reconciliation work "
             "per department. This costs an estimated $450,000 annually in operational overhead."),
            ("Proposed Solution",
             "We will deliver a microservices-based ERP built with Python (FastAPI), React, "
             "and PostgreSQL, hosted on AWS. Key modules: Finance & Accounting, HR & Payroll, "
             "Inventory Management, CRM, Reporting & Analytics."),
            ("Deliverables",
             "1. Requirements analysis document\n"
             "2. System architecture design\n"
             "3. Working ERP with all 5 modules\n"
             "4. Data migration from legacy systems\n"
             "5. User training & documentation\n"
             "6. 12 months post-launch support"),
            ("Timeline",
             "Phase 1 - Discovery & Design: 6 weeks\n"
             "Phase 2 - Core Development: 16 weeks\n"
             "Phase 3 - Testing & QA: 4 weeks\n"
             "Phase 4 - Deployment & Training: 2 weeks\n"
             "Total: 28 weeks (7 months)"),
            ("Budget",
             "Discovery & Design: $35,000\n"
             "Development: $180,000\n"
             "Testing: $25,000\n"
             "Deployment: $15,000\n"
             "Annual Support: $40,000\n"
             "Total Project Cost: $255,000 + $40,000/year support"),
            ("Team",
             "Project Manager: Sarah Chen (PMP certified, 10 years)\n"
             "Lead Architect: David Kim (AWS Solutions Architect)\n"
             "Senior Developers: 3 × full-stack engineers\n"
             "QA Engineer: 1 × ISTQB certified tester\n"
             "UX Designer: 1 × Figma-certified designer"),
            ("Terms & Conditions",
             "Payment: 30% upfront, 40% at Phase 2 completion, 30% at go-live.\n"
             "IP: All custom code is owned by MegaCorp upon final payment.\n"
             "Warranty: 90-day bug-fix warranty post-launch.\n"
             "Confidentiality: NDA in place prior to project start."),
        ],
    },
    {
        "filename": "digital_marketing_proposal.pdf",
        "title": "Digital Marketing Campaign Proposal",
        "content": [
            ("Executive Summary",
             "BrandBoost Agency proposes a 6-month integrated digital marketing campaign "
             "for FreshBrew Coffee Co. to increase online sales by 40% and grow social media "
             "following by 25,000 across Instagram, TikTok, and Facebook."),
            ("Problem Statement",
             "FreshBrew has excellent product quality but lacks digital brand presence. "
             "Current website traffic is 8,000 monthly visits with a 1.2% conversion rate. "
             "Competitors average 45,000 monthly visits with 2.8% conversion."),
            ("Proposed Solution",
             "A multi-channel digital strategy including: SEO optimisation, paid social "
             "advertising (Meta & TikTok Ads), influencer partnerships, content marketing, "
             "and email automation campaigns targeting existing and new customer segments."),
            ("Deliverables",
             "1. SEO audit and keyword strategy\n"
             "2. Monthly content calendar (30 posts/month)\n"
             "3. 5 influencer partnership activations\n"
             "4. Google & Meta Ads management\n"
             "5. Monthly performance reports\n"
             "6. Email automation sequences (5 flows)"),
            ("Timeline",
             "Month 1: Audit, strategy, asset creation\n"
             "Months 2-3: Campaign launch and optimisation\n"
             "Months 4-6: Scale and reporting\n"
             "Monthly review calls every 2 weeks."),
            ("Budget",
             "Agency Retainer (6 months): $18,000\n"
             "Paid Ad Spend Budget: $24,000\n"
             "Influencer Fees: $8,000\n"
             "Content Production: $4,500\n"
             "Total Investment: $54,500"),
            ("Expected ROI",
             "Projected monthly revenue increase: $28,000\n"
             "Break-even point: Month 3\n"
             "6-month ROI: 208%\n"
             "KPIs: website traffic, conversion rate, ROAS, follower growth."),
            ("Team",
             "Account Director: Maria Santos\n"
             "SEO Specialist: James Wright\n"
             "Paid Media Manager: Priya Patel\n"
             "Content Creator: Alex Thompson\n"
             "Data Analyst: Kevin Liu"),
        ],
    },
    {
        "filename": "cloud_migration_proposal.pdf",
        "title": "Cloud Infrastructure Migration Proposal",
        "content": [
            ("Executive Summary",
             "CloudFirst Consulting proposes a phased migration of FinanceCore Ltd's on-premises "
             "infrastructure to Microsoft Azure, reducing infrastructure costs by 35% while "
             "improving uptime SLA from 99.5% to 99.99%."),
            ("Current State Assessment",
             "FinanceCore operates 47 physical servers across 2 data centres. Infrastructure is "
             "8 years old, nearing end-of-life. Annual maintenance cost: $380,000. "
             "Recent incidents: 3 unplanned outages in 12 months averaging 4.2 hours each."),
            ("Proposed Architecture",
             "Migration to Azure with: Azure Kubernetes Service (AKS) for application hosting, "
             "Azure SQL Managed Instance for databases, Azure Blob Storage for files, "
             "Azure Active Directory for identity, ExpressRoute for hybrid connectivity."),
            ("Migration Approach",
             "Phase 1: Non-critical workloads (dev/test environments) - 4 weeks\n"
             "Phase 2: Business applications (CRM, HR systems) - 8 weeks\n"
             "Phase 3: Core financial systems with parallel run - 12 weeks\n"
             "Phase 4: Data centre decommission - 4 weeks"),
            ("Risk Mitigation",
             "All migrations include: parallel running period (2 weeks minimum), "
             "automated rollback procedures, comprehensive testing gates, "
             "24/7 support during cutover windows, cyber insurance coverage."),
            ("Cost Analysis",
             "Migration Project Cost: $95,000\n"
             "Annual Azure Infrastructure: $248,000\n"
             "Annual Savings vs Current: $132,000\n"
             "Payback Period: 8.7 months\n"
             "5-Year NPV Savings: $565,000"),
            ("Compliance & Security",
             "Azure deployments will maintain: ISO 27001, SOC 2 Type II, PCI DSS Level 1, "
             "GDPR compliance. All data encrypted at rest (AES-256) and in transit (TLS 1.3). "
             "Weekly penetration testing and continuous vulnerability scanning."),
            ("Support & Governance",
             "Post-migration: 24/7 NOC monitoring, monthly optimisation reviews, "
             "quarterly business reviews, FinOps dashboard for cost visibility, "
             "Azure Advisor recommendations implemented monthly."),
        ],
    },
]


def create_pdfs():
    try:
        from fpdf import FPDF
    except ImportError:
        print("fpdf2 not installed. Run: pip install fpdf2")
        return

    output_dir = Path(__file__).parent.parent / "data" / "proposals"
    output_dir.mkdir(parents=True, exist_ok=True)

    for proposal in PROPOSALS:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, proposal["title"], ln=True, align="C")
        pdf.ln(5)

        for section_title, section_body in proposal["content"]:
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_fill_color(220, 230, 242)
            pdf.cell(0, 9, section_title, ln=True, fill=True)
            pdf.ln(2)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 7, section_body)
            pdf.ln(4)

        out_path = output_dir / proposal["filename"]
        pdf.output(str(out_path))
        print(f"Created: {out_path}")

    print(f"\nCreated {len(PROPOSALS)} sample proposals in {output_dir}")


if __name__ == "__main__":
    create_pdfs()
