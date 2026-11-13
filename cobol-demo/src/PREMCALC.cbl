      ******************************************************************
      * PREMCALC - DAILY PREMIUM AND INTEREST ACCRUAL
      *
      * A deliberately ordinary batch job: read a fixed-width policy
      * file, work out instalments and accrued interest, write a
      * fixed-width report plus a control total.
      *
      * It is written the way this kind of program actually gets
      * written, which means it carries the things that make migration
      * hard, not the things that make a demo pretty:
      *
      *   - COMP-3 packed decimal with a fixed scale, so arithmetic
      *     TRUNCATES where a naive Java port would round
      *   - PERFORM VARYING ... UNTIL, whose boundary is off by one
      *     from a Java while-loop if translated literally
      *   - A status flag derived from several conditions, where the
      *     order of the IF chain decides the answer
      *   - MOVE of a longer field into a shorter one, which silently
      *     truncates on the left for numerics
      *   - A control total accumulated as the records go past, so one
      *     wrong record shifts a number nobody is reading closely
      ******************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PREMCALC.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT POLICY-FILE ASSIGN TO "policies.dat"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT REPORT-FILE ASSIGN TO "legacy_out.txt"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.

       FD  POLICY-FILE.
       01  POLICY-REC.
           05  IN-POLICY-ID        PIC X(10).
           05  IN-START-DATE       PIC X(8).
           05  IN-PRINCIPAL        PIC 9(7)V99.
           05  IN-RATE-BP          PIC 9(5).
           05  IN-TERM-DAYS        PIC 9(4).
           05  IN-INSTALMENTS      PIC 9(2).
           05  IN-TIER             PIC X(1).

       FD  REPORT-FILE.
       01  REPORT-REC              PIC X(80).

       WORKING-STORAGE SECTION.

       01  WS-EOF                  PIC X VALUE "N".
           88  END-OF-INPUT        VALUE "Y".

      * Fixed scale of two decimals. This is where truncation lives:
      * every COMPUTE into one of these drops the third decimal.
       01  WS-CALC.
           05  WS-DAILY-RATE       PIC S9(1)V9(9) COMP-3.
           05  WS-INTEREST         PIC S9(7)V99   COMP-3.
           05  WS-INSTAL-AMT       PIC S9(7)V99   COMP-3.
           05  WS-RUNNING          PIC S9(7)V99   COMP-3.
           05  WS-TOTAL-DUE        PIC S9(7)V99   COMP-3.

       01  WS-COUNTERS.
           05  WS-I                PIC 9(3) COMP.
           05  WS-ACCRUAL-DAYS     PIC 9(4) COMP.
           05  WS-REC-COUNT        PIC 9(6) COMP VALUE 0.

      * Control total. PIC 9(9)V99 holds up to 999,999,999.99 - the
      * running sum can exceed that on a big file, and COBOL truncates
      * the high-order digits silently. Left in on purpose.
       01  WS-CONTROL.
           05  WS-SUM-DUE          PIC S9(9)V99 COMP-3 VALUE 0.

       01  WS-STATUS               PIC X(2).

       01  WS-OUT-LINE.
           05  O-POLICY-ID         PIC X(10).
           05  O-ACCRUAL-DAYS      PIC 9(4).
           05  O-INSTAL-AMT        PIC 9(7).99.
           05  O-INTEREST          PIC 9(7).99.
           05  O-TOTAL-DUE         PIC 9(7).99.
           05  O-STATUS            PIC X(2).
           05  FILLER              PIC X(14) VALUE SPACES.

       01  WS-TRAILER.
           05  FILLER              PIC X(10) VALUE "TRAILER   ".
           05  T-COUNT             PIC 9(6).
           05  T-SUM-DUE           PIC 9(9).99.
           05  FILLER              PIC X(52) VALUE SPACES.

       PROCEDURE DIVISION.

       MAIN-PARA.
           OPEN INPUT POLICY-FILE
           OPEN OUTPUT REPORT-FILE

           PERFORM UNTIL END-OF-INPUT
               READ POLICY-FILE
                   AT END
                       MOVE "Y" TO WS-EOF
                   NOT AT END
                       PERFORM PROCESS-ONE
               END-READ
           END-PERFORM

           PERFORM WRITE-TRAILER

           CLOSE POLICY-FILE
           CLOSE REPORT-FILE
           STOP RUN.

       PROCESS-ONE.
           ADD 1 TO WS-REC-COUNT

      *    Accrual days: capped at the term. The cap is applied with a
      *    straight MOVE, not a loop, so it has no boundary surprise -
      *    the boundary surprise is in the instalment loop below.
           IF IN-TERM-DAYS > 365
               MOVE 365 TO WS-ACCRUAL-DAYS
           ELSE
               MOVE IN-TERM-DAYS TO WS-ACCRUAL-DAYS
           END-IF

      *    Daily rate from basis points. 9 decimals of working room,
      *    then the result lands in a 2-decimal field and truncates.
           COMPUTE WS-DAILY-RATE = IN-RATE-BP / 10000 / 365

           COMPUTE WS-INTEREST =
               IN-PRINCIPAL * WS-DAILY-RATE * WS-ACCRUAL-DAYS

           COMPUTE WS-TOTAL-DUE = IN-PRINCIPAL + WS-INTEREST

      *    Instalments. PERFORM VARYING ... UNTIL runs the body for
      *    WS-I = 1 .. IN-INSTALMENTS, because the UNTIL is tested
      *    BEFORE the body and the increment happens after. Translating
      *    this to `while (i <= n)` is right; `while (i < n)` is the
      *    classic off-by-one, and so is forgetting that WS-I ends at
      *    n+1 rather than n.
           MOVE 0 TO WS-RUNNING
           COMPUTE WS-INSTAL-AMT = WS-TOTAL-DUE / IN-INSTALMENTS

           PERFORM VARYING WS-I FROM 1 BY 1
                   UNTIL WS-I > IN-INSTALMENTS
               ADD WS-INSTAL-AMT TO WS-RUNNING
           END-PERFORM

      *    Rounding residue: instalments rarely sum back to the total,
      *    because each one was truncated to two decimals. The last
      *    instalment absorbs the difference. Get this wrong and the
      *    money is off by cents - which is exactly the class of
      *    difference a comparator has to decide about.
           COMPUTE WS-INSTAL-AMT =
               WS-INSTAL-AMT + (WS-TOTAL-DUE - WS-RUNNING)

      *    Status. The order of these tests decides the answer for a
      *    record that satisfies more than one. A port that reorders
      *    them - or turns them into independent ifs - changes results
      *    for exactly the overlapping records and nothing else.
           EVALUATE TRUE
               WHEN IN-TIER = "3" AND IN-PRINCIPAL > 4000000
                   MOVE "PD" TO WS-STATUS
               WHEN WS-ACCRUAL-DAYS = 365
                   MOVE "MX" TO WS-STATUS
               WHEN IN-INSTALMENTS = 1
                   MOVE "LS" TO WS-STATUS
               WHEN OTHER
                   MOVE "AP" TO WS-STATUS
           END-EVALUATE

           ADD WS-TOTAL-DUE TO WS-SUM-DUE

           MOVE IN-POLICY-ID    TO O-POLICY-ID
           MOVE WS-ACCRUAL-DAYS TO O-ACCRUAL-DAYS
           MOVE WS-INSTAL-AMT   TO O-INSTAL-AMT
           MOVE WS-INTEREST     TO O-INTEREST
           MOVE WS-TOTAL-DUE    TO O-TOTAL-DUE
           MOVE WS-STATUS       TO O-STATUS

           MOVE WS-OUT-LINE TO REPORT-REC
           WRITE REPORT-REC.

       WRITE-TRAILER.
           MOVE WS-REC-COUNT TO T-COUNT
           MOVE WS-SUM-DUE   TO T-SUM-DUE
           MOVE WS-TRAILER   TO REPORT-REC
           WRITE REPORT-REC.
