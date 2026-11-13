#!/usr/bin/perl
#
# premcalc.pl - daily premium and interest accrual
#
# Written the way this kind of thing actually survives in a bank or a telco:
# one file, no modules beyond core, no tests, written once around 2004 and
# touched twice since. The style is deliberate. A migration team meets code
# like this, not code like a textbook.
#
# The business rules live in ../SPEC.md. What is NOT in the spec - how many
# decimals each step keeps, whether it truncates or rounds, which status wins
# when a record matches two rules - is decided here, silently, the way the
# original author decided it. That is the whole point of the exercise.
#
#   perl legacy/premcalc.pl policies.dat legacy_out.txt

use strict;
use warnings;

my $infile  = shift || 'policies.dat';
my $outfile = shift || 'legacy_out.txt';

open(my $IN,  '<', $infile)  or die "cannot read $infile: $!";
open(my $OUT, '>', $outfile) or die "cannot write $outfile: $!";

my $count   = 0;
my $sum_due = 0;

while (my $line = <$IN>) {
    chomp $line;
    $line =~ s/\r$//;
    next if $line =~ /^\s*$/;

    # Fixed-width unpack. A: space-padded text.
    my ($id, $start, $principal_raw, $rate_bp, $term_days, $instalments, $tier)
        = unpack('A10 A8 A9 A5 A4 A2 A1', $line);

    # Amount carries two implied decimals and no point.
    my $principal = $principal_raw / 100;

    # ---- rule 1: accrual days, capped at 365 -------------------------------
    my $accrual_days = $term_days > 365 ? 365 : $term_days;

    # ---- rules 2+3: interest ------------------------------------------------
    # Everything here is an IEEE double. No fixed-point anywhere. The result is
    # cut to two decimals by sprintf at the very end, not step by step.
    my $daily_rate = ($rate_bp / 10000) / 365;
    my $interest   = $principal * $daily_rate * $accrual_days;

    # ---- rule 4: total due --------------------------------------------------
    my $total_due = $principal + $interest;

    # ---- rules 5+6: instalments and the residue -----------------------------
    # Each instalment is rounded to cents as it is produced; the last one takes
    # whatever is left so the parts add back to the whole.
    my $instal = sprintf('%.2f', $total_due / $instalments) + 0;
    my $running = $instal * ($instalments - 1);
    my $last    = sprintf('%.2f', $total_due - $running) + 0;

    # The report shows ONE instalment figure. For a plan with more than one
    # instalment this program shows the LAST one, because that is the odd one
    # and the one support gets asked about. The spec does not say which.
    my $instal_shown = $instalments > 1 ? $last : $instal;

    # ---- rule 7: status -----------------------------------------------------
    # First match wins, top to bottom. The spec says "exactly one code" but
    # never says which rule outranks which.
    my $status;
    if ($tier eq '3' && $principal > 40000) {
        $status = 'PD';
    } elsif ($accrual_days == 365) {
        $status = 'MX';
    } elsif ($instalments == 1) {
        $status = 'LS';
    } else {
        $status = 'AP';
    }

    # ---- rule 8: control total ---------------------------------------------
    # Accumulated as a float, over the unrounded total. Drift is invisible here
    # and shows up only at the trailer.
    $sum_due += $total_due;
    $count++;

    printf $OUT "%-10s%04d%10.2f%10.2f%10.2f%-2s%-14s\n",
        $id, $accrual_days, $instal_shown, $interest, $total_due, $status, '';
}

printf $OUT "%-10s%06d%12.2f%-52s\n", 'TRAILER', $count, $sum_due, '';

close $IN;
close $OUT;
