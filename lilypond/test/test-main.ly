\version "2.25.26"

Qwe = \new StaffGroup <<
  \new Staff = "upper" {
    \clef treble
    \time 2/4

    % Simple ties
   < c' e' g' c'' >2 |

    c'4 ~ c'4 |

    % More complex ties across bar lines
    e'2~ | e'2~ |
    e'2 | f'2~ |
    f'4 r | g'2~ |
    g'2 |

    % Mixed tied and untied notes
    a'4~ a'8 b'8 |
    
    \bar "|."
  }

  \new Staff = "lower" {
    \clef bass
    \time 2/4

    % Bass line with ties
    c,2~ |
    c,4 d4 |

    % Long ties in bass
    e2~ |
    e2 | f2~ |
    f4 r | g2~ |
    g4 a8 b8 |

    % Mixed patterns
    a,4~ a,8 b,8 | c4 d4 |

    \bar "|."
  }
>>


