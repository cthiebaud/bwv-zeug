\version "2.24.0"

\include "tie-attributes.ily"

\header {
  title = "Simple Tie Test"
  subtitle = "Testing ties within measure, across measures, and chords"
}

\score {
  {
    \clef treble
    \time 4/4
    
    % 1. Tie within measure
    c'2~ c'4 d'4 |
    
    % 2. Tie spanning 2 measures  
    e'1~ |
    e'2 f'2 |
    
    % 3. Simple tie chain (3 notes)
    g'2~ g'2~ |
    g'4 a'4 |
    
    % 4. Chord ties
    <b' d'' f''>2~ <b' d'' f''>2 |
    
    \bar "|."
  }
  
  \layout {
    \context {
      \Voice
      \consists \Tie_data_engraver
    }
  }
}