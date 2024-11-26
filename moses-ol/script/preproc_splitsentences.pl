#!/usr/bin/env perl
#
# BB 16.06.2022
#
# Preprocessor for the script ~/mosesdecoder/scripts/ems/support/split-sentences.perl
# which encounters a problem when reading a line which only consists of a single blank character
# (message "Use of uninitialized value in concatenation (.) or string at /home/mt/mosesdecoder/scripts/ems/support/split-sentences.perl line 245, <STDIN> line xxx.)
#

binmode(STDIN, ":utf8");
binmode(STDOUT, ":utf8");
binmode(STDERR, ":utf8");

use warnings;
use strict;
#use String::Util qw(trim);


while(<STDIN>) {
	chomp($_);    
	$_ =~ s/^\s+|\s+$//g ;     # remove both leading and trailing whitespace

	print $_."\n";
}
