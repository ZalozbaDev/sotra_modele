#!/usr/bin/perl

# Test-Sentence-splitter, der jedes Wort zu einem Satz splittet

use utf8;

binmode(STDIN, ":encoding(UTF-8)");
binmode(STDOUT, ":encoding(UTF-8)");
binmode(STDERR, ":encoding(UTF-8)");

my $ret="";
while(<STDIN>) {
	chomp($_);    
	# print "?".$_."?\n";
	$ret = $ret.$_;
}
my @words = split / /, $ret;

foreach (@words) {
  print $_."\n";
}

#¶