/*
Focuses on the scale and size of the subfigures

<SubHeaderBox>Scale</SubHeaderBox>
                <Grid container spacing={1}>
                    <Grid item xs={6}>
                        <TextField
                            id="outlined-number"
                            label="Min"
                            type="number"
                            InputLabelProps={{
                                shrink: true,
                            }}
                            size="small"
                            sx={{ width: 200}}
                        />
                    </Grid>
                    <Grid item xs={6}>
                        <TextField
                            id="outlined-number"
                            label="Max"
                            type="number"
                            InputLabelProps={{
                                shrink: true,
                            }}
                            size="small"
                            sx={{ width: 200}}
                        />
                    </Grid>
                </Grid>
                <Typography id="Confidence Threshold" gutterBottom sx={{ height: 10}}>
                    Specify confidence threshold:
                </Typography>
                <Slider
                    aria-label="Confidence Threshold"
                    defaultValue={0.3}
                    valueLabelDisplay="auto"
                    step={0.1}
                    marks
                    min={0.1}
                    max={1.0}
                    size="small"
                />
*/