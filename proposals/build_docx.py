#!/usr/bin/env python3
"""Generate the Credico proposal as a Word document from the agreed content."""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

NAVY = RGBColor(0x0D, 0x1B, 0x2A)
TEAL = RGBColor(0x00, 0x78, 0x6A)

doc = Document()

# Base style
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)

def heading(text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(14)
    r.font.color.rgb = TEAL
    p.space_before = Pt(10)
    return p

def para(text, bold=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    return p

def bullet(text):
    doc.add_paragraph(text, style="List Bullet")

# Title
t = doc.add_paragraph()
tr = t.add_run("MULTI-BOARD JOB ADVERTISING")
tr.bold = True
tr.font.size = Pt(20)
tr.font.color.rgb = NAVY
t2 = doc.add_paragraph()
t2r = t2.add_run("Proposal for Credico")
t2r.bold = True
t2r.font.size = Pt(14)
t2r.font.color.rgb = TEAL

doc.add_paragraph()
for label, val in [("Prepared for:", "Credico Marketing Limited"),
                   ("Attention:", "Alicia Harris"),
                   ("Prepared by:", "Talent Finder")]:
    p = doc.add_paragraph()
    rl = p.add_run(label + " ")
    rl.bold = True
    p.add_run(val)

doc.add_paragraph("_" * 60)

# Overview
heading("Overview")
para("Dear Alicia,")
para("This proposal is based on a like-for-like service to what Credico currently uses "
     "through Talent Finder — multi job board advertising. Each credit covers one role, "
     "advertised across our job board network.")

# Job boards
heading("Job Boards")
para("Each credit advertises your role across:")
for b in ["Indeed", "CV Library", "Reed", "Find a Job"]:
    bullet(b)
p = doc.add_paragraph()
r = p.add_run("Job boards can be added or removed — this is a guide.")
r.italic = True

# Inclusions
heading("What Each Credit Includes")
for item in ["Job advert creation",
             "Job posting",
             "Use of our recruitment ATS — add as many hiring managers as required",
             "Full account management support",
             "Priority admin support",
             "Advice on salary and positioning"]:
    bullet(item)

# Pricing
heading("Pricing")
table = doc.add_table(rows=1, cols=3)
table.style = "Light Grid Accent 1"
hdr = table.rows[0].cells
for i, h in enumerate(["Credits", "Price per credit", "Total"]):
    hdr[i].paragraphs[0].add_run(h).bold = True
for credits, price, total in [("100 credits", "£170", "£17,000"),
                              ("300 credits", "£136", "£40,800"),
                              ("500 credits", "£122", "£61,000"),
                              ("800 credits", "£102", "£81,600")]:
    cells = table.add_row().cells
    cells[0].text = credits
    cells[1].text = price
    cells[2].text = total
p = doc.add_paragraph()
p.add_run("All prices exclude VAT.").italic = True

# Add-on
heading("Optional Add-On — Automated Screening & Interview Scheduling")
para("For an additional £75 + VAT per role:")
bullet("All applicants are automatically screened to your required criteria")
bullet("Interviews are automatically scheduled based on each hiring manager's availability")
para("This service will help Credico reduce staffing costs.")

# Tailored
heading("Fully Tailored")
para("This proposal can be fully tailored once we fully understand Credico's actual "
     "requirements. Job boards can be added or removed — this is just a guide.")

# About
heading("About Talent Finder")
para("Talent Finder has been established for 10 years and has the technological "
     "infrastructure to support Credico's growth.")

# Sign-off
doc.add_paragraph("_" * 60)
doc.add_paragraph()
para("Best regards,")
doc.add_paragraph()
para("Riz", bold=True)
para("Talent Finder")

out = "/home/user/TF-pipeline-/proposals/Credico_Multi-Board_Advertising_Proposal.docx"
doc.save(out)
print("Saved", out)
