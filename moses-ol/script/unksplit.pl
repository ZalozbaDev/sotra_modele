#!/usr/bin/perl
open my $fh, '<', $ARGV[0]  or die "Can't open file $!";
# print "File $ARGV[0] opened\n";
my $file_content = do { local $/; <$fh> };
my @words = split ' ', $file_content;
my $str = '';
foreach ( @words ) {
	# print "<unk>$_</unk>";
	$str = $str . "<unk>$_</unk> ";
}
# print "Ergebnis: $str \n";
open(FH, '>', $ARGV[1]) or die $!;
print FH $str;
close(FH);
