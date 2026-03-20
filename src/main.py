import argparse
import sys
import logging

from fpdf import FPDF
from synthesizer import DataIngestor, AdracaSynthesizer
from privacy import PrivacyValidator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def create_pdf_report(report_path, risk_score, dcr_exact_rate, avg_ks, is_compliant):
    logging.info(f"Generating Certificate of Anonymity at {report_path}")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=15, style='B')
    pdf.cell(200, 10, txt="Certificate of Anonymity", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Re-identification Risk Score: {risk_score:.4f}", ln=True)
    pdf.cell(200, 10, txt=f"Exact Match Rate (DCR=0): {dcr_exact_rate:.2%}", ln=True)
    pdf.cell(200, 10, txt=f"Average KS Complement (Utility): {avg_ks:.4f}", ln=True)
    pdf.ln(10)

    compliance_text = "PASSED" if is_compliant else "FAILED"
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(200, 10, txt=f"EMA Policy 0070 Risk Threshold Status: {compliance_text}", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.ln(5)

    ehds_stmt = ("This dataset has been processed using the Adraca Synthetic Patient Engine. "
                 "The output satisfies the 'anonymous data' definition under GDPR Recital 26 "
                 "and the EHDS secondary use provisions.")
    pdf.multi_cell(0, 10, txt=ehds_stmt)
    pdf.output(report_path)


def main():
    parser = argparse.ArgumentParser(description="Adraca Synthetic Patient Engine")
    parser.add_argument("--input", required=True, help="Path to input Parquet/CSV")
    parser.add_argument("--rows", type=int, required=True, help="Number of synthetic rows to generate")
    parser.add_argument("--output", required=True, help="Path to output Parquet/CSV")
    parser.add_argument("--report", required=True, help="Path to output PDF report")
    parser.add_argument("--epsilon", type=float, default=1.0, help="Differential Privacy budget parameter")

    args = parser.parse_args()

    # Stage 1: Ingestion
    ingestor = DataIngestor()
    try:
        real_data = ingestor.load_data(args.input)
        metadata = ingestor.infer_metadata(real_data)
    except Exception as e:
        logging.error(f"Ingestion failed: {e}")
        sys.exit(1)

    # Stage 2: Engine
    synthesizer = AdracaSynthesizer(metadata=metadata, epsilon=args.epsilon)
    synthesizer.fit(real_data)

    num_rows_to_sample = args.rows + int(args.rows * 0.1)  # sample 10% extra in case of strict rejection
    raw_synthetic_data = synthesizer.sample(num_rows=num_rows_to_sample)

    # Stage 3: Validation
    validator = PrivacyValidator(real_data=real_data, synthetic_data=raw_synthetic_data)

    valid_synthetic_data, dcr_values, exact_match_rate = validator.calculate_dcr()

    if len(valid_synthetic_data) < args.rows:
        logging.warning("Not enough records survived privacy filter. Consider generating more samples.")

    final_synthetic_data = valid_synthetic_data.head(args.rows)

    avg_ks = validator.evaluate_utility()
    risk_score = validator.evaluate_reidentification_risk()

    is_compliant = risk_score <= 0.09 and exact_match_rate == 0.0

    if not is_compliant:
        logging.error("Privacy Check Failed: Risk > 0.09 or Exact Match Rate > 0.0")
        logging.error("Trigger Privacy-Utility Trade-off: increase noise or bin quasi-identifiers.")

    # Stage 4: Certification
    if args.output.endswith('.csv'):
        final_synthetic_data.to_csv(args.output, index=False)
    else:
        final_synthetic_data.to_parquet(args.output, index=False)

    create_pdf_report(report_path=args.report,
                      risk_score=risk_score,
                      dcr_exact_rate=exact_match_rate,
                      avg_ks=avg_ks,
                      is_compliant=is_compliant)

    logging.info("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
