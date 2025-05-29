\version "2.25.26"

% docker run -v ".:/work" codello/lilypond:dev --svg -I /work/includes test/test_ties.ly 1>logs/test_ties.log 2>&1 && mv test_ties*.* target

\include "tie-attributes.ily"

\header {
  title = "Test Ties with Data Attributes"
  subtitle = "Testing data-tie attributes on tied note heads with grouped staves"
}

% Test with the custom engraver - two grouped staves
\score {
  \new StaffGroup <<
    \new Staff = "upper" {
      \clef treble
      \time 2/4
      
      % Simple ties
      c'2~ | c'4 d'4 |
      
      % More complex ties across bar lines
      e'1~ |
      e'2 | f'2~ |
      f'4 r | g'2.~ |
      g'2 |
      
      % ties in chord
      <c' e' g'~>4 <c' e' g'> |
      
      % Mixed tied and untied notes
      a'4~ a'8 b'8 | c''4 | d''4 |
      
      \bar "|."
    }
    
    \new Staff = "lower" {
      \clef bass
      \time 4/4
      
      % Bass line with ties
      c2~ c4 d4 |
      
      % Long ties in bass
      e1~ |
      e2 f2~ |
      f4 g2.~ |
      g1 |
      
      % Bass chord ties
      <c e g>2~ <c e g>2 |
      
      % Mixed patterns
      a,4~ a,8 b,8 c4 d4 |
      
      \bar "|."
    }
  >>
  
  \layout {
    \context {
      \Voice
      \consists \Tie_data_engraver
    }
  }
  
  \midi { }
}

