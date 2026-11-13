import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/**
 * PremCalc - daily premium and interest accrual.
 *
 * Reimplementation of a legacy batch job, written from the business
 * specification in SPEC.md. The original source was deliberately not consulted
 * while writing this: the point of the exercise is to produce the code a
 * competent Java developer would write when handed that document, including
 * the choices that document leaves open.
 *
 * Choices made here, and why:
 *
 *   - BigDecimal with HALF_UP for every monetary value. For money in Java in
 *     2026 this is not really a decision; doubles are how you end up explaining
 *     a cent to an auditor.
 *   - Rounding applied at each step as values land in money-scaled fields,
 *     rather than once at print time.
 *   - Rule 5 defines "the instalment amount" and rule 6 describes adjusting the
 *     last one. The report has a single instalment column, so it shows the
 *     amount from rule 5.
 *   - "over 40,000.00" read literally as strictly greater than.
 *   - Status rules evaluated in the order the spec lists them, first match
 *     wins, since the spec says a policy carries exactly one code.
 *
 *   javac PremCalc.java && java PremCalc policies.dat modern_out.txt
 */
public final class PremCalc {

    private static final int MONEY_SCALE = 2;
    private static final int CAP_DAYS = 365;
    private static final BigDecimal BP_DIVISOR = new BigDecimal("10000");
    private static final BigDecimal DAYS_IN_YEAR = new BigDecimal("365");
    private static final BigDecimal PD_THRESHOLD = new BigDecimal("40000.00");

    /** Working precision for the daily rate before it meets money. */
    private static final int RATE_SCALE = 12;

    public static void main(String[] args) throws IOException {
        Path in = Path.of(args.length > 0 ? args[0] : "policies.dat");
        Path out = Path.of(args.length > 1 ? args[1] : "modern_out.txt");

        int count = 0;
        BigDecimal sumDue = BigDecimal.ZERO.setScale(MONEY_SCALE);

        try (BufferedReader r = Files.newBufferedReader(in, StandardCharsets.US_ASCII);
             BufferedWriter w = Files.newBufferedWriter(out, StandardCharsets.US_ASCII)) {

            String line;
            while ((line = r.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }
                Policy p = Policy.parse(line);
                Result res = calculate(p);

                w.write(String.format(Locale.ROOT, "%-10s%04d%10.2f%10.2f%10.2f%-2s%-14s",
                        p.id, res.accrualDays, res.instalment, res.interest,
                        res.totalDue, res.status, ""));
                w.newLine();

                sumDue = sumDue.add(res.totalDue);
                count++;
            }

            w.write(String.format(Locale.ROOT, "%-10s%06d%12.2f%-52s",
                    "TRAILER", count, sumDue, ""));
            w.newLine();
        }
    }

    // ---------------------------------------------------------------- input

    private record Policy(String id, String startDate, BigDecimal principal,
                          int rateBp, int termDays, int instalments, String tier) {

        static Policy parse(String line) {
            String padded = line.length() < 39 ? String.format("%-39s", line) : line;
            return new Policy(
                    padded.substring(0, 10).trim(),
                    padded.substring(10, 18).trim(),
                    // nine digits with two implied decimals
                    new BigDecimal(padded.substring(18, 27).trim())
                            .movePointLeft(2).setScale(MONEY_SCALE),
                    Integer.parseInt(padded.substring(27, 32).trim()),
                    Integer.parseInt(padded.substring(32, 36).trim()),
                    Integer.parseInt(padded.substring(36, 38).trim()),
                    padded.substring(38, 39));
        }
    }

    private record Result(int accrualDays, BigDecimal instalment,
                          BigDecimal interest, BigDecimal totalDue, String status) { }

    // ------------------------------------------------------------ the rules

    private static Result calculate(Policy p) {
        // Rule 1
        int accrualDays = Math.min(p.termDays, CAP_DAYS);

        // Rule 2
        BigDecimal dailyRate = new BigDecimal(p.rateBp)
                .divide(BP_DIVISOR, RATE_SCALE, RoundingMode.HALF_UP)
                .divide(DAYS_IN_YEAR, RATE_SCALE, RoundingMode.HALF_UP);

        // Rule 3
        BigDecimal interest = p.principal
                .multiply(dailyRate)
                .multiply(new BigDecimal(accrualDays))
                .setScale(MONEY_SCALE, RoundingMode.HALF_UP);

        // Rule 4
        BigDecimal totalDue = p.principal.add(interest);

        // Rule 5
        BigDecimal instalment = totalDue
                .divide(new BigDecimal(p.instalments), MONEY_SCALE, RoundingMode.HALF_UP);

        // Rule 7 - first match wins, in spec order
        String status;
        if ("3".equals(p.tier) && p.principal.compareTo(PD_THRESHOLD) > 0) {
            status = "PD";
        } else if (accrualDays == CAP_DAYS) {
            status = "MX";
        } else if (p.instalments == 1) {
            status = "LS";
        } else {
            status = "AP";
        }

        return new Result(accrualDays, instalment, interest, totalDue, status);
    }

    private PremCalc() { }
}
