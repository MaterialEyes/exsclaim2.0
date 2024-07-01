# Pull official image
FROM node:current-alpine AS appbuild

# set the working direction
WORKDIR /app

# install app dependencies
COPY package.json ./
COPY package-lock.json ./

RUN npm install

COPY . ./

RUN npm run build

FROM node:current-alpine AS prod

WORKDIR /app

ENV PATH /app/node_modules/.bin:$PATH

COPY package.json ./
RUN npm install

CMD ["npm", "start"]

COPY --from=appbuild /app/dist ./dist


# Using install_and_run.sh due to a issue that occurred from running
# npm install in the Dockerfile and then attaching a volume to allow
# live updates. The root of the issue is that npm install creates 
# node_modules in container, and mounting local directory afterward
# made node_modules match the possible incorrect local node_modules.
# Three solutions were considered:
#     idea: use bash script to run npm install AFTER bind mount and 
#         then npm start (check that node_modules doesn't exist)
#     idea: have users npm install locally -- potential mess of 
#         different versions? defeats whole purpose of Docker
#     idea: modify node modules path and move to different directory 
#         in container -- lose syntax highlighting and nice features
#CMD ["sh", "./install_and_run.sh"]