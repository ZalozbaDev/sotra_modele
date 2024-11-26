#!/usr/bin/perl
#
use utf8;
use Encode      qw( decode_utf8 );

binmode(STDIN, ":encoding(UTF-8)");
binmode(STDOUT, ":encoding(UTF-8)");
binmode(STDERR, ":encoding(UTF-8)");

use warnings;
use strict;
use File::Temp qw/ tempfile tempdir /;

use File::Basename;


my $num_args = $#ARGV + 1;
if ($num_args < 2) {
	invocation();
}
my $mode = $ARGV[0];
my $lang = $ARGV[1];

#print STDERR "starting main_splitsequences $mode $lang\n";

my $newline_marker="¶";
my $sentence_marker="┊";
my $unknown_marker="??";


if ($mode eq "in"){
	if ($num_args != 3) {
		invocation();
	}
	my $filename_with_controlchars=$ARGV[2];
	my $curscriptdirname = dirname(__FILE__);

	#my $sentence_marker="%";

	my $split_sequence_orig_script = "./mosesdecoder/scripts/ems/support/split-sentences.perl -q -l";
	#my $split_sequence_orig_script = $curscriptdirname."/split_sequences_test.pl";
	#print "I'm here: ".$curscriptdirname."\n";

	my $fh_out;
	open($fh_out, '>', $filename_with_controlchars) or die $!;
	binmode( $fh_out, ":utf8" );
	while(<STDIN>) {
		chomp($_);    
		$_ =~ s/^\s+|\s+$//g ;     # remove both leading and trailing whitespace (trim)

		#print "|".$_."|\n";
		
		# write line to temporary file (instead of passing via stdout - maybe this could cause problems with utf8 encoding)
		my $fh_tmp;
		my $tmp_filename_line;
		
		($fh_tmp, $tmp_filename_line) = tempfile();
		binmode( $fh_tmp, ":utf8" );
		print $fh_tmp $_;
		close($fh_tmp);
		
		
		# $splitted_sequences = `ls`;
		my $splitted_sequences_raw = qx( cat $tmp_filename_line | perl $split_sequence_orig_script $lang );
		my $splitted_sequences = decode_utf8($splitted_sequences_raw);
		# Die via "\n"  gesplitteten Sätze gehen nach STDOUT (ein String!)
		print $splitted_sequences;
		# Ersetze "\n" "mittendrin" durch "┊\n"
		$splitted_sequences =~ s/\n/$sentence_marker\n/g ;
		# Ersetze "\n" am Ende des Strings durch "¶\n"
		$splitted_sequences =~ s/$sentence_marker\n$/$newline_marker\n/g ;
		print $fh_out $splitted_sequences;

		unlink $tmp_filename_line;
	}

	close $fh_out;
	#print STDERR "finished main_splitsequences in\n";
	#print STDERR qx( ls -l $filename_with_controlchars );

} elsif ($mode eq "out"){
	if ($num_args != 4) {
		invocation();
	}
	my $inputfilename_with_controlchars=$ARGV[2];
	my $outputfilename_with_controlchars=$ARGV[3];

	my @splitted_lines;
	#print STDERR qx( ls -l $inputfilename_with_controlchars );
	#print STDERR "filesize ".(-s $inputfilename_with_controlchars)."\n";
	open my $fh_in, $inputfilename_with_controlchars or die "Could not open $inputfilename_with_controlchars: $!";
	binmode( $fh_in, ":utf8" );
	while ( my $line = <$fh_in>){
		chomp($line);
		#print STDERR "line: ".$line."\n";
    	push @splitted_lines, $line;
	}
	close $fh_in;
	#print STDERR $inputfilename_with_controlchars." read!\n";
	#print STDERR "length splitted_lines is ".($#splitted_lines + 1)."\n";
	my $fh_out;
	open($fh_out, '>', $outputfilename_with_controlchars) or die $!;
	binmode( $fh_out, ":utf8" );
	my $ix=0;
	my $splitted_outputline;
	while(<STDIN>) {
		chomp($_);
		$splitted_outputline=$_;
		my $curline = $splitted_lines[$ix];
		my $suffix_end_newline = $newline_marker;
		my $suffix_end_sentence =  $sentence_marker;
		if ($suffix_end_newline eq substr($curline, -length($suffix_end_newline))){
			$splitted_outputline .= $newline_marker;
		} elsif ($suffix_end_sentence eq substr($curline, -length($suffix_end_sentence))){
			$splitted_outputline .= $sentence_marker;
		} else {
			$splitted_outputline .= $unknown_marker;
		}
		print $fh_out $splitted_outputline."\n";
		++$ix;
	}
	close $fh_out;
} else {
	invocation();
}

sub invocation {
    print "\nUsage: main_splitsentences.pl (in|out) language_code input_filename_with_controlchars [output_filename_with_controlchars]\n";
    exit;
}
