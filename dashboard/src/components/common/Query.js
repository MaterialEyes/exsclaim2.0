import React from 'react';
import { useState, useEffect } from 'react';
import { Box, Grid, Paper, styled, Stack } from '@mui/material';
import OutputName from '../inputs/OutputName';
import JournalFamily from '../inputs/JournalFamily';
import NumArticles from '../inputs/NumArticles';
import SortBy from '../inputs/SortBy';
import OpenAccess from '../inputs/OpenAccess';
import InputTerm from '../inputs/InputTerm';
import InputSynonyms from '../inputs/InputSynonyms';
import InputButton from '../inputs/InputButton';

// One big container containing the input query menu for the user to run EXSCLAIM

const HeaderBox = styled(Paper)(({ theme }) => ({
  backgroundColor: '#0cb1f7',
  ...theme.typography.b1,
  padding: theme.spacing(1),
  textAlign: 'center',
  color: '#fff',
  width: '100%'
}));
  
const boxDefault = {
  width: '95%',
  height: 400,
  padding: 2,
  justifyContent: "center",
  display: 'flex',
  m: 2,
}

const Query = () => {

  const [outputName, setOutputName] = useState(""); // set output EXSCLAIM result file name
  const [numArticles, setNumArticles] = useState(0); // set number of articles to parse
  const [term, setTerm] = useState(""); // set term
  const [synonyms, setSynonyms] = useState([]); // set synonyms
  const [journalFamily, setJournalFamily] = useState("nature"); // set the journal family
  const [sort, setSort] = useState("revelant"); // set sort type
  const [access, setAccess] = useState(false); // set open-access or not

  // all props that need to be passed to other components                                        
  const allProps = {
    outputName: outputName,
    numArticles: numArticles,
    term: term,
    synonyms: synonyms,
    journalFamily: journalFamily,
    sort: sort,
    access: access
  }
  
  return (
    <div>
      <Box sx={boxDefault}>
        <Box sx={{ width: "70%" }}>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <HeaderBox>Input Query</HeaderBox>
            </Grid>

            <Grid item xs={6}>
              <Stack spacing={1}>
                <OutputName setOutputName={setOutputName} />
                <NumArticles setNumArticles={setNumArticles} />
                <InputTerm setTerm={setTerm} />
                <InputSynonyms setSynonyms={setSynonyms} />
              </Stack>
            </Grid>

            <Grid item xs={6}>
              <Stack spacing={1}>
                <JournalFamily setJournalFamily={setJournalFamily} />
                <SortBy setSort={setSort} />
                <OpenAccess access={access} setAccess={setAccess} />
                <InputButton {...allProps} />
              </Stack>
            </Grid>
          </Grid>
        </Box>
      </Box> 
    </div>
  )
}
  
export default Query;