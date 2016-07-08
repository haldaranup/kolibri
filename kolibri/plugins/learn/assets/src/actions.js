const Kolibri = require('kolibri');

/**
 * Action to fetch a particular content node from the API.
 * @param {Function} dispatch - The dispatch method of the store object.
 * @param {String} id - The id of the model to be fetched.
 */
const fetchFullContent = ({ dispatch }, id) => {
  // Get the model from ContentNodeResource.
  if (typeof id === 'undefined') {
    id = 'root'; // eslint-disable-line no-param-reassign
  }
  const contentModel = Kolibri.resources.ContentNodeResource.getModel(id);
  // Check to see if it is already synced from the server.
  if (contentModel.synced) {
    // If so, immediately dispatch the mutation to set the attributes of the model into the store.
    dispatch('SET_FULL_CONTENT', contentModel.attributes);
  } else {
    // Otherwise, perform the fetch, and if the promise resolves, then call the mutation.
    contentModel.fetch().then(() => {
      dispatch('SET_FULL_CONTENT', contentModel.attributes);
    });
  }
};

/**
 * Function to dispatch mutations to topics and contents by node kind.
 * @param {Object[]} nodes - Data to dispatch mutations with.
 * @param {Function} dispatch - dispatch method of Vuex Store.
 */
const nodeAssignment = (nodes, dispatch) => {
  const topics = nodes.filter((node) => node.kind === 'topic');
  const contents = nodes.filter((node) => node.kind !== 'topic');

  // clean up API response
  contents.forEach(content => {
    if (!content.progress) {
      content.progress = 'unstarted'; // eslint-disable-line no-param-reassign
    }
    if (!content.thumbnail) {
      content.files.forEach(file => {
        if (file.thumbnail) {
          content.thumbnail = file.storage_url; // eslint-disable-line no-param-reassign
        }
      });
    }
  });

  dispatch('SET_TOPICS', topics);
  dispatch('SET_CONTENTS', contents);
};

/**
 * Action to fetch child topics of a particular topic from the API.
 * @param {Function} dispatch - The dispatch method of the store object.
 * @param {String} id - The id of the model to fetch the children of.
 */
const fetchNodes = ({ dispatch }, id) => {
  // Get the collection from ContentNodeResource.
  if (typeof id === 'undefined') {
    id = 'root'; // eslint-disable-line no-param-reassign
  }
  const contentCollection = Kolibri.resources.ContentNodeResource.getCollection({ parent: id });
  if (contentCollection.synced) {
    nodeAssignment(contentCollection.data, dispatch);
  } else {
    contentCollection.fetch().then(() => {
      nodeAssignment(contentCollection.data, dispatch);
    });
  }
};


const searchNodes = ({ dispatch }, params, page) => {
  // Get the collection from ContentNodeResource.
  const pageSize = 12;
  const contentCollection = Kolibri.resources.ContentNodeResource.getPagedCollection({
    search: params,
  }, {
    pageSize,
    page,
  });
  contentCollection.fetch().then(() => {
    const nodes = contentCollection.data;
    const topics = nodes.filter((node) => node.kind === 'topic');
    const contents = nodes.filter((node) => node.kind !== 'topic');
    const pagesum = contentCollection.pageCount;
    dispatch('SET_SEARCH_TOPICS', topics);
    dispatch('SET_SEARCH_CONTENTS', contents);
    dispatch('SET_SEARCH_PAGES', pagesum);
  });
};

const searchToggleSwitch = ({ dispatch }, params) => {
  dispatch('SET_SEARCH_TOGGLED', params);
};

module.exports = {
  fetchFullContent,
  fetchNodes,
  searchNodes,
  searchToggleSwitch,
};
