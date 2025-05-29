\version "2.25.26"

\include "tie-attributes.ily"

\header {
  title = "Simple Tie Test"
  subtitle = "Minimal test for debugging tie attributes"
}

% Very simple test - just one tie
\score {
  {
    \clef treble
    \time 4/4
    
    % Just one simple tie
    % c'2~ c'4 r4 |
    % Just 2 ties
    { c'2~ c'2~ c'4 r4 }
    
    \bar "|."
  }
  
  \layout {
    \context {
      \Voice
      \consists \Tie_data_engraver
    }
  }
}