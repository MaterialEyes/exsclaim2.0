/*

Focuses on the keywords contained in the subfigures

<SubHeaderBox>Keywords</SubHeaderBox>
                <Autocomplete
                    disablePortal
                    id="combo-box-demo"
                    options={keywords}
                    sx={{ width: 300, height: 30 }}
                    renderInput={(params) => <TextField {...params} label="Keywords" />}
                    size="small"
                />
                <FormGroup>
                    <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Subfigure's Distributed Caption" />
                    <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Subfigure's Containing Figure's Caption" />
                    <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Article Title" />
                </FormGroup>
*/