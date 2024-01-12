#!/usr/bin/env python
from __future__ import print_function

## Author: Chris Wymant, c.wymant@imperial.ac.uk
## Acknowledgement: I wrote this while funded by ERC Advanced Grant PBDR-339251
##
## Overview:
ExplanatoryMessage = '''This script retrieves searched-for sequences from a
fasta file. Output is printed to stdout in fasta format.'''

import argparse
import os
import sys
from Bio import SeqIO
import collections

# Define a function to check files exist, as a type for the argparse.
def File(MyFile):
  if not os.path.isfile(MyFile):
    raise argparse.ArgumentTypeError(MyFile+' does not exist or is not a file.')
  return MyFile
# Define a function to convert from a comma-separated pair of positive integers
# as a string, to a list of two integers, as a type for the argparse.
def CoordPair(MyCoordPair):
  if MyCoordPair.count(',') != 1:
    raise argparse.ArgumentTypeError(MyCoordPair+\
    ' does not contain exactly 1 comma.')
  LeftCoord, RightCoord = MyCoordPair.split(',')
  try:
    LeftCoord, RightCoord = int(LeftCoord), int(RightCoord)
  except ValueError:
    raise argparse.ArgumentTypeError('Unable to understand the values in'+\
    MyCoordPair+' as integers.')
  if LeftCoord > RightCoord:
    raise argparse.ArgumentTypeError('The left value should not be greater '+\
    'than the right value in '+MyCoordPair)
  if LeftCoord < 1:
    raise argparse.ArgumentTypeError('The left value should be greater than'+\
    ' or equal to 1 in '+MyCoordPair)
  return [LeftCoord,RightCoord]

# Set up the arguments for this script
ExplanatoryMessage = ExplanatoryMessage.replace('\n', ' ').replace('  ', ' ')
parser = argparse.ArgumentParser(description=ExplanatoryMessage)
parser.add_argument('FastaFile', type=File)
parser.add_argument('SequenceName', nargs='+')
parser.add_argument('-v', '--invert-search', action='store_true', \
help='return all sequences except those searched for')
parser.add_argument('-W', '--window', type=CoordPair,\
help='A comma-separated pair of positive integers specifying the coordinates'+\
' (with respect to the alignment if the sequenced are aligned) of a window '+\
'outside of which the desired sequences will be truncated / trimmed / not '+\
'printed. e.g. specifying 2,10 means only the second to tenth positions in '+\
'desired sequence(s) will be printed.')
parser.add_argument('-g', '--gap-strip', action='store_true', \
help='Remove all gap characters ("-" and "?") before printing. NB if '+\
'multiple sequences are being retrieved from an alignment, this will probably'+\
' unalign them. NB if used in conjunction with -W, fewer bases than the '+\
'window width may be printed.')
parser.add_argument('-S', '--match-start', action='store_true', \
help='Sequences whose names begin with one of the strings-to-be-searched for '+\
'are returned.')
parser.add_argument('-B', '--skip-blanks', action='store_true', \
help='Sequences consisting entirely of gap characters ("-" and "?") are '+\
'ignored. (By default they are included.)')
parser.add_argument('--max-gap-frac', type=float, \
help='Sequences whose fraction of gap characters ("-" and "?") exceeds the '
'threshold specified with this option will be ignored. (By default they are '
'included.)')

args = parser.parse_args()

# Check all sequences to be searched for are unique
CounterObject = collections.Counter(args.SequenceName)
DuplicatedArgs = [i for i in CounterObject if CounterObject[i]>1]
if len(DuplicatedArgs) != 0:
  for DuplicatedArg in DuplicatedArgs:
    print('Sequence name', DuplicatedArg, 'was duplicated in the arguments.',\
    file=sys.stderr)
  print('All sequence names should be unique. Exiting.', file=sys.stderr)
  exit(1)

# Sanity check of max gap frac
HaveMaxGapFrac = args.max_gap_frac != None
if HaveMaxGapFrac and not (0 <= args.max_gap_frac < 1):
  print('The value specified with --max-grap-frac should be equal to or greater'
  ' than 0 and less than 1. Quitting.', file=sys.stderr)
  exit(0)

NumSeqsToSearchFor = len(args.SequenceName)

# Find the seqs
AllSeqNamesEncountered = []
SeqsWeWant = []
SeqsWeWant_names = []
for seq in SeqIO.parse(open(args.FastaFile),'fasta'):
  AllSeqNamesEncountered.append(seq.id)
  if args.match_start:
    ThisSeqWasSearchedFor = False
    for beginning in args.SequenceName:
      if seq.id[0:len(beginning)] == beginning:
        ThisSeqWasSearchedFor = True
        break
  else:
    ThisSeqWasSearchedFor = seq.id in args.SequenceName
  if ThisSeqWasSearchedFor and (not args.invert_search):
    if seq.id in SeqsWeWant_names:
      print('Sequence', seq.id, 'occurs multiple times in', args.FastaFile+\
      '\nQuitting.', file=sys.stderr)
      exit(1)
    SeqsWeWant.append(seq)
    SeqsWeWant_names.append(seq.id)
    if not args.match_start and len(SeqsWeWant) == NumSeqsToSearchFor:
      break
  elif args.invert_search and (not ThisSeqWasSearchedFor):
    if seq.id in SeqsWeWant_names:
      print('Sequence', seq.id, 'occurs multiple times in', args.FastaFile+\
      '\nQuitting.', file=sys.stderr)
      exit(1)
    SeqsWeWant.append(seq)
    SeqsWeWant_names.append(seq.id)

# Check we found some sequences for printing!
if SeqsWeWant == []:
  print('Found no sequences to print. Quitting.', file=sys.stderr)
  exit(1)

# Check all specified seqs were encountered (unless only the beginnings of names
# were specified).
if not args.match_start:
  SeqsNotFound = [seq for seq in args.SequenceName \
  if not seq in AllSeqNamesEncountered]
  if len(SeqsNotFound) != 0:
    print('The following sequences were not found in', args.FastaFile+':', \
    ' '.join(SeqsNotFound) +'\nQuitting.', file=sys.stderr)
    exit(1)

# Trim to the specified window and/or gap strip, if desired
if args.window != None:
  LeftCoord, RightCoord = args.window
  for seq in SeqsWeWant:
    if RightCoord > len(seq.seq):
      print('A window', LeftCoord, '-', RightCoord, 'was specified but', \
      seq.id, 'is only', len(seq.seq), 'bases long. Quitting.', file=sys.stderr)
      exit(1)
    seq.seq = seq.seq[LeftCoord-1:RightCoord]
    if args.gap_strip:
      seq.seq = seq.seq.ungap("-").ungap("?")

# Skip blank sequences if desired
if args.skip_blanks:
  NewSeqsWeWant = []
  for seq in SeqsWeWant:
    if len(seq.seq.ungap("-").ungap("?")) != 0:
      NewSeqsWeWant.append(seq)
  SeqsWeWant = NewSeqsWeWant

# Skip overly gappy seqs if desired
if HaveMaxGapFrac:
  NewSeqsWeWant = []
  for seq in SeqsWeWant:
    SeqAsStr = str(seq.seq)
    if float(SeqAsStr.count("-") + SeqAsStr.count("?")) / len(SeqAsStr) <= \
    args.max_gap_frac:
      NewSeqsWeWant.append(seq)
  SeqsWeWant = NewSeqsWeWant

SeqIO.write(SeqsWeWant, sys.stdout, "fasta")
