#!/usr/bin/perl

use warnings;
use strict;

run() unless caller();
use Getopt::Std;

my $debug = $ENV{DEBUG} || 0;

sub run {
	my %opts;
	if(!getopts('ch',\%opts) || $opts{h}) {
		print "Usage: perl $0 [-c][-h] < in > out\n";
		exit;
	}
	my $neSymbol = $opts{m} || '@ne@';
	while(<>) {
		chomp;
		print mark_nes($_,$opts{c},$neSymbol,$_),"\n";
	}
}

sub mark_nes {
	my $input = shift;
	my $corpusMode = shift;

	my $output = $input;
	my $found;
	my $replacement;

	while($input =~ /├(.*?)┤/g) {
		$found = $replacement = $1;
		$found = "├".$found."┤";
		$replacement =~ s/ //g;
		$replacement =~ s/@-@/-/g;
		if($corpusMode) {
			# No Tags
		}
		else {
			$replacement = "<n translation=\"".$replacement."\">".$replacement."</n>";
		}
		# \Q .. \E for escaping of arbitrary characters in $found
		$output =~ s/\Q$found\E/$replacement/;
	}

	return $output;
}

1;
